# -*- coding: utf-8

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
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

from django.db import models

from pykol.models.base import ModuleElementaireFormation, MEFMatiere

class Grille(models.Model):
	"""
	Grille de référence pour la répartition des crédits ECTS entre les
	matières d'un même module de formation.
	"""
	code_mef = models.ForeignKey(ModuleElementaireFormation,
		on_delete=models.CASCADE)
	ref = models.CharField(max_length=50)
	nom = models.CharField(max_length=100, blank=True, null=False)

	SEMESTRE_UN = constantes.PERIODE_PREMIERE
	SEMESTRE_DEUX = constantes.PERIODE_DEUXIEME
	SEMESTRE_CHOICES = (
		(SEMESTRE_UN, "semestre 1"),
		(SEMESTRE_DEUX, "semestre 2"),
	)
	semestre = models.PositiveSmallIntegerField(choices=SEMESTRE_CHOICES)

	objects = GrilleManager()

	class Meta:
		unique_together = ('code_mef', 'ref', 'semestre')

	def __str__(self):
		if self.nom:
			return self.nom
		else:
			return '{classe} - {semestre}'.format(
					classe=self.code_mef.libelle,
					semestre=self.get_semestre_display())

class GrilleGroupeLignes(models.Model):
	"""
	Groupe de lignes dans une grille ECTS
	"""
	libelle = models.CharField(max_length=100, blank=False,
			verbose_name="libellé")
	grille = models.ForeignKey(Grille, on_delete=models.CASCADE,
			related_name="groupes_lignes")
	position = models.PositiveSmallIntegerField(default=0)

	def __str__(self):
		return self.libelle

class GrilleLigne(models.Model):
	"""
	Ligne donnant le nombre de crédits d'une matière dans une grille
	ECTS.
	"""
	libelle = models.CharField(max_length=100, blank=True, default="")
	grille = models.ForeignKey(Grille, on_delete=models.CASCADE,
		related_name="lignes")
	groupe = models.ForeignKey(GrilleGroupeLignes,
			on_delete=models.CASCADE, related_name="lignes", blank=True,
			null=True)
	position = models.PositiveSmallIntegerField(default=0)

	credits = models.PositiveSmallIntegerField(verbose_name="crédits")
	matiere = models.ForeignKey(MEFMatiere, on_delete=models.CASCADE,
			verbose_name="matière")
	force_creation = models.BooleanField(
			verbose_name="forcer la création",
			help_text="Quand cette option est activée, la ligne est "
			"ajoutée systématiquement aux attestations ECTS des "
			"étudiants, même si aucun enseignement ne correspond dans "
			"la classe ou si l'étudiant ne suit aucune option "
			"correspondant à cette matière. Ceci permet de pallier "
			"certaines défectuosités (notamment pour la chimie en PCSI "
			"dans les nomenclatures SIECLE.")

class GrilleMatchLigne(models.Model):
	"""
	Condition sur les options de l'étudiant pour que la grille
	s'applique à lui. Une grille ECTS ne s'applique à un étudiant que si
	ce dernier suit toutes les options indiquées par les
	GrilleMatchLigne de cette grille.
	"""
	grille = models.ForeignKey(Grille, on_delete=models.CASCADE,
		related_name="match_options")
	matiere = models.ForeignKey(MEFMatiere, on_delete=models.CASCADE,
			verbose_name="matière")
