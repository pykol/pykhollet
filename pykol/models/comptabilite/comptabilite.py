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

	decouvert_duree = models.DurationField(default=timedelta,
			verbose_name="durée à découvert autorisée")

	decouvert_duree_interrogation = models.DurationField(
			default=timedelta,
			verbose_name="durée d'interrogation à découvert autorisée")

	def __str__(self):
		return self.nom

	def solde(self, annee):
		"""
		Calcul du solde du compte pour l'année donnée en paramètre.

		Cette méthode renvoie une liste de dictionnaires, chaque
		dictionnaire donne la durée totale et la durée d'interrogation
		pour un taux donné.
		"""
		comptes = self.get_descendants(include_self=True)

		return MouvementLigne.objects.filter(compte__in=comptes,
			mouvement__annee=annee).values('taux').aggregate(duree=models.Sum('duree'),
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

	def __str__(self):
		return self.motif

	@classmethod
	@transaction.atomic
	def virement(cls, compte_debit, compte_credit,
			duree, duree_interrogation=None,
			taux=None, **kwargs):
		"""
		Méthode de classe pour faciliter la création d'un virement
		simple d'heures d'un compte à un autre.
		"""
		mv = cls(**kwargs)
		mv.save()

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

	@transaction.atomic
	def virement_retour(self, lettrage=True):
		"""
		Crée un virement retour qui annule le mouvement actuel.

		La ligne de crédit du mouvement actuel sera lettrée avec la
		ligne de débit du mouvement retour si le paramètre lettrage vaut
		True.
		"""
		mv = Mouvement(annee=self.annee,
			motif="Annulation du mouvement {pk}".format(pk=self.pk))
		mv.save()

		for ligne in self.lignes.all():
			# Ceci provoque la création d'une nouvelle instance lors de
			# la sauvegarde.
			ligne.pk = None
			ligne.duree = -ligne.duree
			ligne.duree_interrogation = -ligne.duree_interrogation
			ligne.mouvement = mv
			ligne.save()

		if lettrage:
			lignes_lettrage = self.lignes.filter(duree__gt=timedelta()
				).union(mv.lignes.filter(duree__lt=timedelta()))
			Lettrage.lettrage_total(lignes_lettrage)

		return mv

	def solde(self):
		return self.lignes.aggregate(duree=models.Sum('duree'),
				duree_interrogation=models.Sum('duree_interrogation'))

	def est_equilibre(self):
		solde = self.solde()
		return solde['duree'] == timedelta() and \
				solde['duree_interrogation'] == timedelta()

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
		durees = lignes.aggregate(duree=Sum('duree'),
			duree_interrogation=Sum('duree_interrogation'))
		if durees['duree'] != timedelta() or \
			durees['duree_interrogation'] != timedelta():
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
		lignes.update(lettrage=lettrage)
		return lettrage

class ColleDureeTaux(models.Model):
	TAUX_1A_INF20 = 1
	TAUX_1A_INF35 = 2
	TAUX_1A_SUP36 = 3
	TAUX_2A_INF20 = 4
	TAUX_2A_INF35 = 5
	TAUX_2A_SUP36 = 6

	TAUX_CHOICES = (
		(TAUX_1A_INF20, "1è année - Moins de 20 étudiants"),
		(TAUX_1A_INF35, "1è année - Entre 21 et 35 étudiants"),
		(TAUX_1A_SUP36, "1è année - Plus de 35 étudiants"),
		(TAUX_2A_INF20, "2è année - Moins de 20 étudiants"),
		(TAUX_2A_INF35, "2è année - Entre 21 et 35 étudiants"),
		(TAUX_2A_SUP36, "2è année - Plus de 35 étudiants"),
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
