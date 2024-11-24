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

from django.db import models
from django.db.models import Q

from pykol.models.base import Annee, Enseignement, Classe, Etudiant, \
		Matiere, Etablissement
from pykol.models import constantes
from pykol.models.comptabilite import Compte, Mouvement
from .colles import Colle

class Dotation(models.Model):
	"""Délégation d'heures de colles par le rectorat"""

	annee = models.ForeignKey(Annee, on_delete=models.CASCADE)
	date = models.DateField()
	heures = models.IntegerField(verbose_name="nombre d'heures")
	etablissement = models.ForeignKey(Etablissement,
			on_delete=models.CASCADE)

	def comptabiliser(self):
		"""
		Crée le mouvement de compte qui correspond à cette dotation
		d'heures.
		"""
		duree = self.heures * timedelta(hours=1)
		mv = Mouvement.objects.virement(
			annee=self.annee,
			compte_debit=self.etablissement.academie.compte_dotation,
			compte_credit=self.etablissement.compte_colles,
			duree=duree,
			duree_interrogation=duree_interrogation,
			motif="Dotation en heures du {date}".format(date=self.date),
			date=self.date)
		mv.valider()
		return mv

class CollesEnseignement(models.Model):
	"""
	Dotation en heures de colle pour les différents enseignements d'une
	classe.
	"""

	nomenclature_id = models.CharField(max_length=100, blank=True)

	nom = models.CharField(max_length=100, blank=True)

	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	# Liste des enseignements qui partagent cette dotation
	enseignements = models.ManyToManyField(Enseignement)

	FREQUENCE_HEBDOMADAIRE = 1
	FREQUENCE_TRIMESTRIELLE = 2
	FREQUENCE_CHOICES = (
			(FREQUENCE_HEBDOMADAIRE, 'par semaine'),
			(FREQUENCE_TRIMESTRIELLE, 'par trimestre'),
		)
	frequence = models.SmallIntegerField(verbose_name="fréquence",
			choices=FREQUENCE_CHOICES)
	duree_frequentielle = models.DurationField(
			verbose_name="durée fréquentielle")

	PERIODE_ANNEE = constantes.PERIODE_ANNEE
	PERIODE_PREMIERE = constantes.PERIODE_PREMIERE
	PERIODE_DEUXIEME = constantes.PERIODE_DEUXIEME
	PERIODE_CHOICES = constantes.PERIODE_CHOICES
	periode = models.SmallIntegerField(verbose_name="période",
			choices=PERIODE_CHOICES, default=PERIODE_ANNEE)

	MODE_INTERROGATION = Colle.MODE_INTERROGATION
	MODE_TD = Colle.MODE_TD
	MODE_CHOICES = Colle.MODE_CHOICES
	mode_defaut = models.PositiveSmallIntegerField(
			verbose_name="mode par défaut",
			choices=MODE_CHOICES,
			default=MODE_INTERROGATION)

	compte_colles = models.ForeignKey(Compte, on_delete=models.PROTECT)

	@property
	def duree(self):
		"""
		Durée d'interrogation par élève d'une colle.

		Par défaut, on considère que les colles à fréquence
		hebdomadaire d'après la réglementation sont effectuées à un
		rythme qui permet des interrogations de 20 minutes. Ainsi, si la
		réglementation prévoit 5 minutes par semaine et par élève, la
		colle est programmée une fois toutes les 4 semaines.

		Pour les colles trimestrielles, on prend la durée indiquée pour
		la période.
		"""
		if self.frequence == CollesEnseignement.FREQUENCE_HEBDOMADAIRE:
			return timedelta(minutes=20)
		else:
			return self.duree_frequentielle

	def dotation(self, enseignement=None):
		"""
		Calcule la dotation en heures de colles théorique pour un
		enseignement donné. Si l'enseignement n'est pas précisé, on
		calcule la dotation globale pour tous les enseignements.
		"""
		if enseignement:
			# TODO vérifier que l'enseignement est bien dans la liste ?
			enseignements = [enseignement]
		else:
			enseignements = self.enseignements.all()

		# On réalise l'union des listes d'étudiants avant de compter,
		# pour ne pas compter plusieurs fois le même étudiant sur une
		# dotation partagée entre plusieurs matières.
		etudiants_qs = Etudiant.objects.none()
		for enseignement in enseignements:
			etudiants_qs = etudiants_qs.union(enseignement.etudiants.sur_ventilation_service(self.classe.annee))

		nb_etudiants = etudiants_qs.distinct().count()

		if self.frequence == CollesEnseignement.FREQUENCE_HEBDOMADAIRE:
			if self.periode == CollesEnseignement.PERIODE_ANNEE:
				mult = self.classe.get_nb_semaines_colles()
			elif self.periode == CollesEnseignement.PERIODE_PREMIERE:
				mult = constantes.SEMAINES_PREMIERE_PERIODE
			else: # Deuxième période
				mult = self.classe.get_nb_semaines_colles() - \
						constantes.SEMAINES_PREMIERE_PERIODE
		else:
			mult = self.classe.get_nb_trimestres_colles()

		return nb_etudiants * self.duree_frequentielle * mult

	def meilleure_matiere_enseignements(self, enseignements=None):
		"""
		Étant donné une liste d'enseignements, que l'on suppose liés à
		des matières toutes filles d'une même matière, cette méthode
		renvoie le nom de la matière mère. S'il n'y a pas de matière
		mère stricte, elle renvoie le nom de la matière fille elle-même.
		"""
		if enseignements is None:
			enseignements = self.enseignements.all()

		matiere = Matiere.objects.filter(virtuelle=True,
				filles__enseignement__pk__in=enseignements).first()
		if matiere is not None:
			return matiere
		else:
			return enseignements[0].matiere

	def __str__(self):
		if self.nom:
			nom = self.nom
		else:
			nom = str(self.meilleure_matiere_enseignements())

		return "{classe} - {nom}".format(
			classe=self.classe,
			nom=nom)

class DotationClasse(models.Model):
	classe = models.OneToOneField(Classe, on_delete=models.CASCADE,
			primary_key=True, related_name="dotation_heures")
	heures = models.PositiveIntegerField(verbose_name="nombre d'heures")

class DotationClasseLigne(models.Model):
	dotation_classe = models.ForeignKey(DotationClasse,
			on_delete=models.CASCADE)
	enseignement = models.ForeignKey(Enseignement,
			on_delete=models.CASCADE)
	heures = models.PositiveIntegerField(verbose_name="nombre d'heures")

	def heures_theoriques(self):
		"""
		Calcule la dotation théorique pour cette ligne, d'après les
		données des ColleEnseignement.
		"""
		pass
