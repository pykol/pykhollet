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

import re
import uuid

from django.db import models
from django.db.models import F
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.conf import settings

from pykol.models.fields import Lettre23Field
from pykol.models.base import Etablissement
from pykol.models.comptabilite import Compte
import pykol.lib.files

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

	# On redéfinit cette méthode, présente dans BaseUserManager, car
	# celle d'origine ne prend pas en compte l'option null=True sur le
	# champ email : elle renvoie '' au lieu de None.
	@classmethod
	def normalize_email(cls, email):
		"""
		Normalize the email address by lowercasing the domain part of it.
		"""
		email = email or ''
		try:
			email_name, domain_part = email.strip().rsplit('@', 1)
		except ValueError:
			pass
		else:
			email = email_name + '@' + domain_part.lower()
		return email or None


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

	birth_date = models.DateField(verbose_name="date de naissance",
			null=True, blank=True)

	signature = models.ImageField(blank=True, null=True,
			storage=pykol.lib.files.private_storage,
			upload_to='signature/')

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
		if self.sexe == User.SEXE_HOMME:
			if abrege:
				return 'M.'
			else:
				return 'Monsieur'

		if self.sexe == User.SEXE_FEMME:
			if abrege:
				return 'Mme'
			else:
				return 'Madame'

	def name_civilite(self, abrege=False):
		if abrege:
			return "{civilite} {last}".format(
				civilite=self.civilite(),
				last=self.last_name.upper())
		else:
			return "{civilite} {last} {first}".format(
				civilite=self.civilite(),
				last=self.last_name.upper(),
				first=self.first_name)

	def short_name_civilite(self):
		return self.name_civilite(abrege=True)

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
		try:
			return self.professeur.mes_classes()
		except ObjectDoesNotExist:
			return Classe.objects.none()

class EtudiantQuerySet(models.QuerySet):
	def sur_ventilation_service(self, annee):
		"""
		Filtre les étudiants présents sur les ventilations de service.
		On considère qu'il s'agit des étudiants présents au 15 octobre
		de l'année.
		"""
		quinze_octobre = annee.debut.replace(month=10, day=15)
		return self.filter(models.Q(sortie__isnull=True) |
				models.Q(sortie__gt=quinze_octobre))
	
	def demissionnaire(self, annee=None):
		"""
		Renvoie uniquement les étudiants démissionnaires sur l'année
		donnée. Si l'année n'est pas précisée, cette méthode renvoie
		tous les étudiants qui ont quitté l'établissement.
		"""
		if annee is not None:
			return self.filter(sortie__isnull=False,
					classe__annee=annee)
		else:
			return self.filter(sortie__isnull=False)

class EtudiantManager(UserManager):
	def get_queryset(self):
		return EtudiantQuerySet(self.model, using=self._db)

	def sur_ventilation_service(self, *args, **kwargs):
		return self.get_queryset().sur_ventilation_service(*args, **kwargs)

	def demissionnaire(self, *args, **kwargs):
		return self.get_queryset().demissionnaire(*args, **kwargs)

class Etudiant(User):
	"""
	Étudiant inscrit dans l'établissement
	"""
	origine = models.ForeignKey(Etablissement,
			blank=True, null=True,
			verbose_name="Établissement d'origine",
			on_delete=models.SET_NULL)

	# Dernière classe à laquelle a appartenu l'étudiant
	classe = models.ForeignKey('Classe', on_delete=models.PROTECT)

	# Date d'entrée dans l'établissement
	entree = models.DateField(null=True, blank=True,
			verbose_name="entrée")

	# Date de sortie de l'établissement
	sortie = models.DateField(null=True, blank=True)

	# Numéro INE de l'étudiant. On ne se sert pas de ce numéro comme clé
	# primaire car, dans quelques rares cas, il n'est pas encore
	# attribué au moment de l'inscription.
	ine = models.CharField(max_length=11, verbose_name="INE (numéro d'étudiant)",
			unique=True, blank=True, null=True)
	numero_siecle = models.CharField(max_length=30,
			verbose_name="Numéro interne SIECLE")

	options = models.ManyToManyField('Matiere', through='OptionEtudiant')

	objects = EtudiantManager()

	class Meta:
		verbose_name = "étudiant"
		verbose_name_plural = "étudiants"

	def clean(self):
		super().clean()
		if not self.entree:
			self.entree = self.classe.annee.debut

	def get_absolute_url(self):
		return reverse('etudiant', args=(self.pk,))

class Discipline(models.Model):
	"""
	Discipline d'enseignement des professeurs
	"""
	code = models.CharField(max_length=5, primary_key=True)
	nom = models.CharField(max_length=100)

	def __str__(self):
		return "{} ({})".format(self.nom, self.code)

class ProfesseurManager(UserManager):
	def create(self, **kwargs):
		professeur = self.model(**kwargs)
		professeur.construire_comptes(kwargs.get('commit', True))
		return professeur

class CodeIndemniteMixin(models.Model):
	# Code indemnité applicable au professeur pour le paiement des
	# colles.
	CODE_INDEMNITE_PROF_CPGE = '0207'
	CODE_INDEMNITE_PROF_AUTRE = '2249'
	CODE_INDEMNITE_CHOICES = (
			(CODE_INDEMNITE_PROF_CPGE, "professeur en CPGE"),
			(CODE_INDEMNITE_PROF_AUTRE, "moins d'un demi-service en CPGE"),
	)
	code_indemnite = models.CharField(max_length=4,
			verbose_name="code indemnité",
			choices=CODE_INDEMNITE_CHOICES,
			default=CODE_INDEMNITE_PROF_AUTRE)

	class Meta:
		abstract = True

class Professeur(CodeIndemniteMixin, User):
	"""
	Professeur intervenant dans l'établissement

	Ce modèle peut servir à représenter aussi bien les professeurs
	affectés à l'établissement que les intervenants extérieurs. Le
	statut est précisé grâce au champ corps.
	"""
	objects = ProfesseurManager()

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
			default=CORPS_AGREGE)
	etablissement = models.ForeignKey(Etablissement, null=True,
			blank=True, on_delete=models.SET_NULL,
			verbose_name="établissement")
	disciplines = models.ManyToManyField(Discipline)

	# Éléments d'identification du professeur sur ASIE
	id_acad = models.CharField(max_length=20,
			verbose_name="identifiant académique", blank=True)
	nom_asie = models.CharField(max_length=100,
			verbose_name="Nom du professeur dans ASIE", blank=True,
			help_text="Champ à remplir lorsque le nom affiché pour "
			  "ce professeur ne correspond pas au nom sous lequel il "
			  "est connu dans ASIE. Ce champ peut être laissé vide si "
			  "le nom connu dans ASIE n'est pas différent.")
	prenom_asie = models.CharField(max_length=100,
			verbose_name="Prénom du professeur dans ASIE", blank=True,
			help_text="Champ à remplir lorsque le prénom affiché pour "
			  "ce professeur ne correspond pas au prénom sous lequel il "
			  "est connu dans ASIE. Ce champ peut être laissé vide si "
			  "le prénom connu dans ASIE n'est pas différent.")

	# Comptes de paiement des heures de colles. Quand une heure de colle
	# est programmée au colloscope, une heure de colle est débitée sur
	# le compte de dotation de la classe/de la matière et créditée sur
	# le "compte_prevu" du professeur. Quand le professeur a effectué la
	# colle, l'heure est transférée de "compte_prevu" vers
	# "compte_effectue".
	# Lors de la mise en paiement, les heures sont transférées du
	# "compte_effectue" vers le compte de paiement de relevé d'heures
	# tenu par l'établissement.
	# À la fin de l'année scolaire, les comptes des professeurs
	# devraient avoir un solde nul.
	compte_prevu = models.ForeignKey(Compte, on_delete=models.PROTECT,
			related_name='professeur_prevues')
	compte_effectue = models.ForeignKey(Compte,
			on_delete=models.PROTECT,
			related_name='professeur_effectue')

	class Meta:
		verbose_name = "professeur"
		verbose_name_plural = "professeurs"

	def mes_classes(self):
		"""Liste des classes où le professeur intervient"""
		from pykol.models.base import Classe
		qs = Classe.objects.filter(enseignements__service__professeur=self).union(
				Classe.objects.filter(coordonnateur=self)).union(
				Classe.objects.filter(creneau__colleur=self)).union(
				Classe.objects.filter(colle__colledetails__actif=True,
					colle__colledetails__colleur=self)).union(
				Classe.objects.filter(colle__colledetails__actif=True,
					colle__colledetails__eleves__classe__pk=F('pk'),
					colle__colledetails__colleur=self)).union(
				Classe.objects.filter(
					colloscopepermission__droit__codename='change_colloscope',
					colloscopepermission__user=self))
		return qs

	def construire_comptes(self, commit=True):
		"""
		Initialise les comptes de colle du professeur, s'ils ne sont pas
		déjà définis.
		"""
		if hasattr(self, 'compte_prevu') or \
			hasattr(self, 'compte_effectue'):
			return

		compte_prof = Compte(
			categorie=Compte.CATEGORIE_ACTIFS,
			nom="{last_name} {first_name}".format(
				last_name=self.last_name,
				first_name=self.first_name),
			parent=Etablissement.objects.get(pk=settings.PYKOL_UAI_DEFAUT).compte_professeurs,
			decouvert_autorise=True)
		compte_prof.save()

		compte_prevu = Compte(
			categorie=Compte.CATEGORIE_ACTIFS,
			nom="Colles prévues",
			parent=compte_prof)
		compte_prevu.save()

		compte_effectue = Compte(
			categorie=Compte.CATEGORIE_ACTIFS,
			nom="Colles effectuées",
			parent=compte_prof,
			decouvert_autorise=True)
		compte_effectue.save()

		self.compte_prevu = compte_prevu
		self.compte_effectue = compte_effectue

		if commit:
			self.save()

		if self.pk is not None:
			compte_prof.gestionnaires.add(self)
			compte_prevu.gestionnaires.add(self)
			compte_effectue.gestionnaires.add(self)

class JetonAcces(models.Model):
	uuid = models.UUIDField(default=uuid.uuid4, editable=False,
			primary_key=True)
	owner = models.ForeignKey(User, on_delete=models.CASCADE)
	scope = models.CharField(max_length=100)
