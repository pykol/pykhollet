# -*- coding:utf8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018-2019 Florian Hatat
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


"""Modèles pour la gestion des relevés des heures de colles
effectuées et leur mise en paiement."""

from datetime import timedelta

from django.db import models, transaction
from django.utils.timezone import localtime
from django.template.loader import get_template

from pykol.models.base import Annee, Professeur, Classe, Etablissement
from pykol.models.comptabilite import ColleDureeTaux, Compte, \
		Mouvement, MouvementLigne
from pykol.models.colles import Colle

class ColleReleve(models.Model):
	"""
	Relevé périodique des colles effectuées afin de les mettre en
	paiement.
	"""
	def default_annee():
		return Annee.objects.get_actuelle()

	annee = models.ForeignKey(Annee, default=default_annee,
			on_delete=models.CASCADE)
	date = models.DateTimeField(help_text="Date de création du relevé")
	date_paiement = models.DateTimeField(blank=True, null=True,
			help_text="Date où toutes les colles de ce relevé ont été "
			"mises en paiement.")

	etablissement = models.ForeignKey(Etablissement,
		on_delete=models.CASCADE)

	compte_colles = models.ForeignKey(Compte, on_delete=models.PROTECT)

	ETAT_NOUVEAU = 0
	ETAT_PAYE = 1
	ETAT_CHOICES = (
			(ETAT_NOUVEAU, "Nouveau"),
			(ETAT_PAYE, "Payé"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_NOUVEAU)

	def __str__(self):
		return "Relevé du {date}".format(date=self.date)

	def save(self, *args, **kwargs):
		"""
		Sauvegarde d'un relevé. Si aucun compte n'est attribué à ce
		relevé, on en crée un automatiquement en fonction de
		l'établissement.
		"""
		if self.compte_colles is None:
			self.compte_colles = Compte(
				categorie=Compte.CATEGORIE_ACTIFS,
				parent=self.etablissement.compte_releves,
				nom=str(self))
			self.compte_colles.save()
		super().save(*args, **kwargs)

	class Meta:
		verbose_name = "relevé des colles"
		verbose_name_plural = "relevés des colles"

	@transaction.atomic
	def payer(self, date=None):
		"""
		Marquer le relevé actuel comme intégralement payé.

		Cette méthode ne vérifie pas si chaque ligne du relevé a été
		effectivement payée.
		"""
		if date is None:
			self.date_paiement = localtime()
		else:
			self.date_paiement = date
		self.etat = ColleReleve.ETAT_PAYE
		self.save()

	def maj_etat(self, date=None):
		"""
		Marquer le relevé comme intégralement payé dans le cas où toutes
		les lignes du relevé sont payées. Si une seule ligne n'est pas
		payée, l'état du relevé n'est pas modifié.
		"""
		if not self.lignes.exclude(etat=ColleReleve.ETAT_PAYE).exists():
			self.payer(date)

	@property
	def total_heures(self):
		"""
		Nombre total d'heures mises en paiement dans le relevé.
		"""
		total = self.lignes.aggregate(
				total_heures=models.Sum('duree'))['total_heures'] \
				or timedelta()
		return total.total_seconds() / 3600

	@transaction.atomic
	def ajout_colle(self, colle):
		"""
		Ajout d'une colle au relevé en cours.

		Cette fonction crée ou modifie l'objet ColleReleveLigne
		correspondant à la colle.
		"""
		# On ne paie pas deux fois les colles
		if colle.releve is not None:
			return

		ligne, _ = ColleReleveLigne.objects.get_or_create(
				releve=self,
				colleur=colle.colleur,
				taux=ColleReleveLigne.taux_colle(colle.classe))
		colle.etat = Colle.ETAT_RELEVEE
		colle.releve = self
		colle.save()
		ligne.ajout_colle(colle)

	def lignes_par_prof(self):
		return self.lignes.order_by('colleur__last_name',
				'colleur__first_name', 'taux')

	def get_etat_html(self):
		template = get_template('pykol/widgets/collereleve_etat.html')
		return template.render(context={'object': self})

class ColleReleveLigne(ColleDureeTaux):
	"""
	Une ligne d'un relevé de colles. Une ligne correspond au total des
	heures effectuées par un professeur donné sur la période, et pour un
	seul taux de paiement donné.
	"""
	releve = models.ForeignKey(ColleReleve, on_delete=models.CASCADE,
			related_name='lignes')
	colleur = models.ForeignKey(Professeur, on_delete=models.CASCADE)

	ETAT_NOUVEAU = 0
	ETAT_PAYE = 1
	ETAT_SAISIE_ASIE = 2
	ETAT_CHOICES = (
			(ETAT_NOUVEAU, "Nouveau"),
			(ETAT_PAYE, "Payé"),
			(ETAT_SAISIE_ASIE, "Saisie dans ASIE"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES,
			default=ETAT_NOUVEAU)
	date_paiement = models.DateTimeField(blank=True, null=True)

	# Ligne qui crédite le compte des colles effectuées
	mouvement_ligne = models.OneToOneField(MouvementLigne, on_delete=models.PROTECT)

	@classmethod
	def taux_colle(cls, classe):
		"""
		Détermine le taux d'une colle en fonction de la classe
		"""
		if classe.niveau == Classe.NIVEAU_PREMIERE_ANNEE:
			if classe.effectif <= 20:
				return cls.TAUX_1A_INF20
			elif classe.effectif <= 35:
				return cls.TAUX_1A_INF35
			else:
				return cls.TAUX_1A_SUP36
		else:
			if classe.effectif <= 20:
				return cls.TAUX_2A_INF20
			elif classe.effectif <= 35:
				return cls.TAUX_2A_INF35
			else:
				return cls.TAUX_2A_SUP36

	@property
	def heures(self):
		return self.duree.total_seconds() / 3600

	@property
	def heures_interrogation(self):
		return self.duree_interrogation.total_seconds() / 3600

	def _init_mouvement(self):
		"""
		Initialisation d'un mouvement comptable vide pour cette ligne de
		relevé. Il est nécessaire de sauvegarder manuellement l'instance
		de ColleReleveLigne par la suite, cette méthode ne le fait pas.
		"""
		if self.mouvement_ligne is not None:
			return

		mouvement = Mouvement(
			annee=self.releve.annee,
			date=self.releve.date,
			motif=str(self.releve)
			)
		mouvement.save()

		self.mouvement_ligne = MouvementLigne(
			compte=self.releve.compte_colles,
			mouvement=mouvement,
			duree=timedelta(),
			duree_interrogation=timedelta(),
			taux=taux,
			motif=str(self.releve))
		self.mouvement_ligne.save()

	def save(self, *args, **kwargs):
		"""
		Sauvegarde d'une ligne de relevé.

		Si cette ligne ne possède encore aucun mouvement comptable, on
		l'initialise avant de sauvegarder dans la base.
		"""
		self._init_mouvement()
		self.save(*args, **kwargs)

	def ajout_colle(self, colle):
		"""
		Ajout d'une Colle à la ligne de relevé actuelle
		"""
		# Cette fonction ne vérifie rien du tout (ni que le colleur est
		# le même, ni que la colle a été notée, ni le code de paiement).
		if colle.mode == Colle.MODE_INTERROGATION:
			duree_interrogation = timedelta()
			for collenote in colle.collenote_set.all():
				duree_interrogation += collenote.duree
		else:
			duree_interrogation = colle.duree

		self.duree += colle.duree
		self.duree_interrogation += duree_interrogation

		# Augmentation du mouvement comptable avec cette colle.
		self._init_mouvement()

		# On augmente la ligne de crédit des colles effectuées...
		self.mouvement_ligne.duree = self.duree
		self.mouvement_ligne.duree_interrogation = self.duree_interrogation

		# et on compense par une nouvelle ligne de débit.
		MouvementLigne(
			compte=self.colleur.compte_effectue,
			mouvement=self.mouvement_ligne.mouvement,
			duree=-colle.duree,
			duree_interrogation=-duree_interrogation,
			taux=self.taux,
			motif=str(self.releve)).save()

		self.save()

	@transaction.atomic
	def payer(self, date=None):
		if date is None:
			self.date_paiement = localtime()
		else:
			self.date_paiement = date
		self.etat = ColleReleveLigne.ETAT_PAYE
		self.save()

		self.releve.maj_etat()

	def get_etat_html(self):
		template = get_template('pykol/widgets/collereleve_etat.html')
		return template.render(context={'object': self})
