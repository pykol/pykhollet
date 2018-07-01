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
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.urls import reverse

from pykol.models.fields import Lettre23Field
from pykol.models.base import Etablissement

class UserManager(BaseUserManager):
	"""Define a model manager for User model with no username field."""

	use_in_migrations = True

	def _create_user(self, email, password, **extra_fields):
	    """Create and save a User with the given email and password."""
	    if not email:
	        raise ValueError('The given email must be set')
	    email = self.normalize_email(email)
	    user = self.model(email=email, **extra_fields)
	    user.set_password(password)
	    user.save(using=self._db)
	    return user

	def create_user(self, email, password=None, **extra_fields):
	    """Create and save a regular User with the given email and password."""
	    extra_fields.setdefault('is_staff', False)
	    extra_fields.setdefault('is_superuser', False)
	    return self._create_user(email, password, **extra_fields)

	def create_superuser(self, email, password, **extra_fields):
	    """Create and save a SuperUser with the given email and password."""
	    extra_fields.setdefault('is_staff', True)
	    extra_fields.setdefault('is_superuser', True)

	    if extra_fields.get('is_staff') is not True:
	        raise ValueError('Superuser must have is_staff=True.')
	    if extra_fields.get('is_superuser') is not True:
	        raise ValueError('Superuser must have is_superuser=True.')

	    return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
	"""
	Compte utilisateur de pyKol

	Ce modèle reprend le modèle de base de Django pour les utilisateurs,
	en ajoutant un champ supplémentaire pour stocker le sexe de
	l'utilisateur. Cette information est toujours nécessaire pour les
	traitements administratifs des différentes catégories
	d'utilisateurs.
	"""
	SEXE_HOMME = 1
	SEXE_FEMME = 2
	sexe = models.PositiveSmallIntegerField(choices=(
		(SEXE_HOMME, 'homme'),
		(SEXE_FEMME, 'femme'),
		), default=SEXE_HOMME)

	email = models.EmailField(verbose_name="E-mail", unique=True,
			null=True, blank=True)
	username = None

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = ['sexe',]

	objects = UserManager()

	class Meta:
		verbose_name = "utilisateur"
		verbose_name_plural = "utilisateurs"
		permissions = (
			('direction', "Droits de paramétrage de l'équipe de direction"),
			)

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

	# On redéfinit cette méthode, présente dans BaseUserManager, car
	# celle d'origine ne prend pas en compte l'option null=True sur le
	# champ email : elle renvoie '' au lieu de None.
	@classmethod
	def normalize_email(cls, email):
	    """
	    Normalize the email address by lowercasing the domain part of it.
	    """
	    email = email or None
	    try:
	        email_name, domain_part = email.strip().rsplit('@', 1)
	    except ValueError:
	        pass
	    else:
	        email = email_name + '@' + domain_part.lower()
	    return email

	def __str__(self):
		nom = '{last} {first}'.format(last=self.last_name.upper(),
				first=self.first_name)
		if nom.strip():
			return nom
		else:
			return '({})'.format(self.email)

	def short_display_name(self):
		return '{initials} {last_name}'.format(
				initials=re.sub(r'(\w)\w*', r'\1.', self.first_name),
				last_name=self.last_name.upper())

	def mes_classes(self):
		"""Retourne la liste des classes pertinentes pour cet
		utilisateur"""
		from pykol.models.base import Classe
		if self.has_perm('pykol.direction'):
			return Classe.objects.all()
		else:
			return Classe.objects.none()

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
	ine = models.CharField(max_length=11, verbose_name="INE (numéro d'étudiant)")
	options = models.ManyToManyField('Matiere', blank=True)

	class Meta:
		verbose_name = "étudiant"
		verbose_name_plural = "étudiants"
		unique_together = ['ine']

	def clean(self):
		super().clean()
		if not self.entree:
			self.entree = self.classe.annee.debut

	def get_absolute_url(self):
		return reverse('etudiant', args=(self.pk,))

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

	def mes_classes(self):
		"""Liste des classes où le professeur intervient"""
		from pykol.models.base import Classe
		qs = Classe.objects.filter(enseignements__service__professeur=self).union(
				Classe.objects.filter(coordonnateur=self)).union(
				Classe.objects.filter(creneau__colleur=self))
		return qs
