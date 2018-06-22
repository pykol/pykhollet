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

import re

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from pykol.models.fields import Lettre23Field
from pykol.models.base import Etablissement

class User(AbstractUser):
	"""
	Compte utilisateur de pyKol

	Ce modèle reprend le modèle de base de Django pour les utilisateurs,
	en ajoutant un champ supplémentaire pour stocker le sexe de
	l'utilisateur. Cette information est toujours nécessaire pour les
	traitements administratifs des différentes catégories
	d'utilisateurs.
	"""
	SEXE_HOMME=1
	SEXE_FEMME=2
	sexe = models.PositiveSmallIntegerField(choices=(
		(SEXE_HOMME, 'homme'),
		(SEXE_FEMME, 'femme'),
		), default=SEXE_HOMME)

	REQUIRED_FIELDS = ['email', 'sexe',]

	def civilite(self, abrege=True):
		if self.sexe == SEXE_HOMME:
			if abrege:
				return 'M.'
			else:
				return 'Monsieur'

		if self.sexe == SEXE_FEMME:
			if abrege:
				return 'Mme'
			else:
				return 'Madame'

	def __str__(self):
		nom = '{last} {first}'.format(last=self.last_name.upper(),
				first=self.first_name)
		if nom.strip():
			return nom
		else:
			return '({})'.format(self.username)

	def short_display_name(self):
		return '{initials} {last_name}'.format(
				initials=re.sub(r'(\w)\w*', r'\1.', self.first_name),
				last_name=self.last_name.upper())

	class Meta:
		verbose_name = "utilisateur"
		verbose_name_plural = "utilisateurs"
		permissions = (
			('direction', "Droits de paramétrage de l'équipe de direction"),
			)

class Etudiant(User):
	"""
	Étudiant inscrit dans l'établissement
	"""
	origine = models.ForeignKey(Etablissement,
			blank=True, null=True,
			verbose_name="Établissement d'origine",
			on_delete=models.SET_NULL)
	classe = models.ForeignKey('Classe', on_delete=models.PROTECT)
	entree = models.DateField(null=True, blank=True,
			verbose_name="entrée")
	sortie = models.DateField(null=True, blank=True)
	ine = Lettre23Field(length=11, verbose_name="INE (numéro d'étudiant)")
	options = models.ManyToManyField('Matiere', blank=True)

	class Meta:
		verbose_name = "étudiant"
		verbose_name_plural = "étudiants"
		unique_together = ['ine']

	def clean(self):
		super().clean()
		if not self.entree:
			self.entree = self.classe.annee.debut

class Professeur(User):
	"""
	Professeur intervenant dans l'établissement

	Ce modèle peut servir à représenter aussi bien les professeurs
	affectés à l'établissement que les intervenants extérieurs. Le
	statut est précisé grâce au champ corps.
	"""
	CORPS_AUTRE = 0
	CORPS_CERTIFIE = 1
	CORPS_AGREGE = 2
	CORPS_CHAIRESUP = 3
	LISTE_CORPS = (
			(CORPS_AUTRE, "autre"),
			(CORPS_CERTIFIE, "certifié"),
			(CORPS_AGREGE, "agrégé"),
			(CORPS_CHAIRESUP, "chaire supérieure"),
		)
	corps = models.PositiveSmallIntegerField(choices=LISTE_CORPS,
			default=2)
	etablissement = models.ForeignKey(Etablissement, null=True,
			blank=True, on_delete=models.SET_NULL,
			verbose_name="établissement")

	class Meta:
		verbose_name = "professeur"
		verbose_name_plural = "professeurs"
