# -*- coding:utf8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018 Florian Hatat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from datetime import timedelta

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
#from django.contrib.auth import get_user_model
#User = get_user_model()

from mptt.models import MPTTModel, TreeForeignKey

class Compte(MPTTModel):
	nom = models.CharField(max_length=100)
	parent = TreeForeignKey('self', on_delete=models.CASCADE,
			null=True, blank=True, related_name='sous_comptes')

	gestionnaires = models.ManyToManyField('User', blank=True)

	CATEGORIE_DEPENSES = 0
	CATEGORIE_ACTIFS = 1
	CATEGORIE_REVENUS = 2
	CATEGORIE_DETTES = 3
	CATEGORIE_FONDS_PROPRES = 4
	CATEGORIE_CHOICES = (
		(CATEGORIE_DEPENSES, "compte de dépenses"),
		(CATEGORIE_ACTIFS, "compte d'actifs"),
		(CATEGORIE_REVENUS, "compte de revenus"),
		(CATEGORIE_DETTES, "compte de dettes"),
		(CATEGORIE_FONDS_PROPRES, "compte de fonds propres"),
	)
	categorie = models.SmallIntegerField(verbose_name="type de compte",
			choices=CATEGORIE_CHOICES)

	decouvert_autorise = models.BooleanField(
		default=False,
		verbose_name="découvert autorisé",
		help_text="Ce champ indique si le compte peut être à "
			"découvert. Dans ce cas, on peut limiter le nombre "
			"d'heures du découvert en donnant des valeurs explicites "
			"aux durées à découvert autorisées.")

	decouvert_duree = models.DurationField(
			blank=True, null=True,
			verbose_name="durée à découvert autorisée",
			help_text="Lorsque le découvert est autorisé sur ce "
			"compte, ce champ donne une limite sur le nombre d'heures "
			"comptabilisées négativement. Par exemple, si ce champ "
			"vaut 3h, le solde du compte devra toujours être supérieur "
			"ou égal à -3h.")

	decouvert_duree_interrogation = models.DurationField(
			blank=True, null=True,
			verbose_name="durée d'interrogation à découvert autorisée")

	def __str__(self):
		return self.nom

	def solde(self, annee=None):
		"""
		Calcul du solde du compte pour l'année donnée en paramètre.

		Cette méthode renvoie une liste de dictionnaires, chaque
		dictionnaire donne la durée totale et la durée d'interrogation
		pour un taux donné.
		"""
		if annee is None:
			from pykol.models.base import Annee
			annee = Annee.objects.get_actuelle()

		comptes = self.get_descendants(include_self=True)

		return MouvementLigne.objects.filter(compte__in=comptes,
			mouvement__annee=annee,
			mouvement__etat=Mouvement.ETAT_VALIDE).values('taux'
		).aggregate(duree=models.Sum('duree'),
			duree_interrogation=models.Sum('duree_interrogation'))

	def sens_affichage(self):
		"""
		Renvoie -1 ou 1 pour indiquer si, étant donné sa catégorie, le
		compte doit normalement avoir un solde négatif (notamment pour
		les comptes de revenus) ou un solde positif.
		"""
		if self.categorie in (CATEGORIE_REVENUS, CATEGORIE_DETTES):
			return -1
		else:
			return 1

	def format_duree(self, duree, sens=True):
		"""
		Formate une durée en prenant en compte le sens d'affichage du
		compte.
		"""
		if sens:
			return "{:.2f}".format(self.sens_affichage() *
				duree.total_seconds() / 3600)
		else:
			return "{:.2f}".format(duree.total_seconds() / 3600)

	def retrait_possible(self, ligne):
		"""
		Renvoie True quand le retrait de la ligne donnée en paramètre ne
		provoque pas un dépassement du découvert autorisé.
		"""
		solde = self.solde(ligne.mouvement.annee)

		if self.decouvert_autorise:
			if self.decouvert_duree is None:
				duree_minimale = None
			else:
				duree_minimale = -self.decouvert_duree

			if self.decouvert_duree_interrogation is None:
				duree_interrogation_minimale = None
			else:
				duree_interrogation_minimale = -self.decouvert_duree_interrogation
		else:
			duree_minimale = timedelta()
			duree_interrogation_minimale = timedelta()

		return \
			(duree_minimale is None or
				solde['duree'] - ligne.duree >= duree_minimale) and \
			(duree_interrogation_minimale is None or
				solde['duree_interrogation'] - ligne.duree_interrogation >= \
				duree_interrogation_minimale)

class CompteDecouvert(Exception):
	"""
	Exception levée lorsque la comptabilisation d'un mouvement
	provoquerait le dépassement du découvert autorisé d'un compte.
	"""
	def __init__(self, ligne):
		self.ligne = ligne

class MouvementManager(models.Manager):
	@transaction.atomic
	def virement(self, compte_debit, compte_credit,
			duree, duree_interrogation=None,
			taux=None, **kwargs):
		"""
		Méthode de classe pour faciliter la création d'un virement
		simple d'heures d'un compte à un autre.
		"""
		mv = self.create(**kwargs)

		# Ligne de débit
		MouvementLigne(
			compte=compte_debit,
			mouvement=mv,
			duree=-duree,
			duree_interrogation=-duree_interrogation,
			taux=taux,
			motif=mv.motif).save()

		# Ligne de crédit
		MouvementLigne(
			compte=compte_credit,
			mouvement=mv,
			duree=duree,
			duree_interrogation=duree_interrogation,
			taux=taux,
			motif=mv.motif).save()

		return mv

class MouvementNonEquilibre(Exception):
	pass

class Mouvement(models.Model):
	"""
	Transfert d'heures de colles entre comptes.

	Les mouvements d'heures sont suivis en comptabilité double : pour
	chaque mouvement, on trouve une ou plusieurs lignes de débit sur
	certains d'autres et des lignes de crédit sur d'autres comptes.

	Un mouvement d'heures est une liste de MouvementLigne dont le solde
	doit être équilibré (somme à zéro).
	"""
	annee = models.ForeignKey('Annee', on_delete=models.CASCADE)
	date = models.DateTimeField(default=timezone.now)
	motif = models.CharField(max_length=100)

	# Lien vers une éventuelle colle à l'origine de ce mouvement
	colle = models.ForeignKey('Colle', on_delete=models.SET_NULL,
			blank=True, null=True)

	ETAT_BROUILLON = 0
	ETAT_VALIDE = 1
	ETAT_CHOICES = (
		(ETAT_BROUILLON, "brouillon"),
		(ETAT_VALIDE, "validé"),
	)
	etat = models.SmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_BROUILLON)

	objects = MouvementManager()

	def __str__(self):
		return self.motif

	@transaction.atomic
	def virement_retour(self, lettrage=True):
		"""
		Crée un virement retour qui annule le mouvement actuel.

		La ligne de crédit du mouvement actuel sera lettrée avec la
		ligne de débit du mouvement retour si le paramètre lettrage vaut
		True.
		"""
		motif_retour = "Annulation du mouvement {pk}".format(pk=self.pk)
		mv = Mouvement(annee=self.annee, motif=motif_retour)
		mv.save()

		for ligne in self.lignes.all():
			# Ceci provoque la création d'une nouvelle instance lors de
			# la sauvegarde.
			ligne.pk = None
			ligne.duree = -ligne.duree
			ligne.duree_interrogation = -ligne.duree_interrogation
			ligne.mouvement = mv
			ligne.motif = motif_retour
			ligne.save()

		if lettrage:
			lignes_lettrage = self.lignes.filter(duree__gt=timedelta()
				).union(mv.lignes.filter(duree__lt=timedelta()))
			Lettrage.lettrage_total(lignes_lettrage)

		return mv

	def solde(self):
		"""
		Renvoie la somme des durées des lignes contenues dans ce
		mouvement.
		"""
		return self.lignes.aggregate(duree=models.Sum('duree'),
				duree_interrogation=models.Sum('duree_interrogation'))

	def est_equilibre(self):
		"""
		Indique si la somme des durées des lignes du mouvement est bien
		nulle.
		"""
		solde = self.solde()
		return solde['duree'] == timedelta() and \
				solde['duree_interrogation'] == timedelta()

	@transaction.atomic
	def valider(self):
		"""
		Valide le mouvement à condition qu'il soit équilibré et que les
		soldes des comptes le permettent.
		"""
		# On verrouille les comptes pour éviter toute autre transaction
		# concurrente pendant que l'on vérifie les soldes.
		comptes = Compte.objects.filter(lignes__mouvement=self
			).select_for_update()

		if not self.est_equilibre():
			raise MouvementNonEquilibre()
		for ligne in self.lignes.all():
			if ligne.sens == MouvementLigne.SENS_DEBIT and \
				not ligne.compte.retrait_possible(ligne):
				raise CompteDecouvert(ligne)

		self.etat = self.ETAT_VALIDE
		self.save()

	def _premiere_ligne_sens(self, sens):
		for ligne in self.lignes.all():
			if ligne.sens == sens:
				return ligne

	def ligne_debit(self):
		"""
		Renvoie la première ligne de ce mouvement qui est un débit. Ceci
		permet d'identifier facilement la ligne de débit dans le cas
		d'un virement simple. L'ordre n'est pas défini quand il y a
		plusieurs lignes de débit.
		"""
		return self._premiere_ligne_sens(MouvementLigne.SENS_DEBIT)

	def ligne_credit(self):
		"""
		Renvoie la première ligne de ce mouvement qui est un crédit. Ceci
		permet d'identifier facilement la ligne de crédit dans le cas
		d'un virement simple. L'ordre n'est pas défini quand il y a
		plusieurs lignes de crédit.
		"""
		return self._premiere_ligne_sens(MouvementLigne.SENS_CREDIT)

class LettrageNonEquilibre(Exception):
	pass

class Lettrage(models.Model):
	"""
	Rapprochement de lignes de mouvements.

	Ceci permet de pointer des mouvements qui ont un rapport les uns
	avec les autres. Par exemple pour le compte d'un professeur donné :
	* lorsqu'il effectue une colle, son compte personnel est crédité du
	  nombre d'heures correspondant ;
	* lorsqu'une mise en paiement est effectuée sur ASIE, le compte
	  personnel est débité du nombre d'heures payées ;
	* on peut alors lettrer les lignes de crédit avec cette dernière
	  ligne de débit. Ceci indique alors quelles heures ont été mises en
	  paiement et à quelle date.
	"""
	date = models.DateTimeField(default=timezone.now)

	LETTRAGE_PARTIEL = 0
	LETTRAGE_TOTAL = 1
	LETTRAGE_CHOICES = (
		(LETTRAGE_PARTIEL, "partiel"),
		(LETTRAGE_TOTAL, "total"),
	)
	mode = models.PositiveSmallIntegerField(default=LETTRAGE_PARTIEL,
			choices=LETTRAGE_CHOICES)

	@classmethod
	@transaction.atomic
	def lettrage_total(cls, lignes):
		# On ne fait pas l'hypothèse que lignes est un QuerySet pour
		# permettre à l'appelant de donner à peu près n'importe quel
		# itérable.
		duree = timedelta()
		duree_interrogation = timedelta()

		for ligne in lignes:
			duree += ligne.duree
			duree_interrogation += ligne.duree_interrogation

		if duree != timedelta() or duree_interrogation != timedelta():
			raise LettrageNonEquilibre

		lettrage = cls.lettrage_partiel(lignes)
		lettrage.mode = cls.LETTRAGE_TOTAL
		lettrage.save()
		return lettrage

	@classmethod
	@transaction.atomic
	def lettrage_partiel(cls, lignes):
		lettrage = cls(mode=cls.LETTRAGE_PARTIEL)
		lettrage.save()

		for ligne in lignes:
			ligne.lettrage = lettrage
			ligne.save()

		return lettrage

class ColleDureeTaux(models.Model):
	TAUX_1A_INF20 = 1
	TAUX_1A_INF35 = 2
	TAUX_1A_SUP36 = 3
	TAUX_2A_INF20 = 4
	TAUX_2A_INF35 = 5
	TAUX_2A_SUP36 = 6

	TAUX_CHOICES = (
		(TAUX_1A_INF20, "1è année - 19 étudiants ou moins"),
		(TAUX_1A_INF35, "1è année - Entre 20 et 35 étudiants"),
		(TAUX_1A_SUP36, "1è année - À partir de 36 étudiants"),
		(TAUX_2A_INF20, "2è année - 19 étudiants ou moins"),
		(TAUX_2A_INF35, "2è année - Entre 20 et 35 étudiants"),
		(TAUX_2A_SUP36, "2è année - À partir de 36 étudiants"),
		)
	taux = models.PositiveSmallIntegerField(blank=True, null=True,
			verbose_name="taux", choices=TAUX_CHOICES)
	duree_interrogation = models.DurationField(
			verbose_name="durée d'interrogation", default=timedelta)
	duree = models.DurationField(verbose_name="nombre d'heures",
			default=timedelta)

	class Meta:
		abstract = True

class MouvementLigne(ColleDureeTaux):
	"""
	Ligne d'un mouvement sur un compte.

	Dans un même mouvement, la somme de toutes les lignes doit être
	nulle.
	"""
	compte = models.ForeignKey(Compte, on_delete=models.CASCADE,
			related_name='lignes')
	mouvement = models.ForeignKey(Mouvement, related_name='lignes',
			on_delete=models.CASCADE)

	motif = models.CharField(blank=True, max_length=100)
	lettrage = models.ForeignKey(Lettrage, related_name='lignes',
			blank=True, null=True, on_delete=models.SET_NULL)

	SENS_DEBIT = -1
	SENS_CREDIT = 1

	@property
	def sens(self):
		if self.duree >= timedelta() and \
				self.duree_interrogation >= timedelta():
			return self.SENS_CREDIT
		else:
			return self.SENS_DEBIT
