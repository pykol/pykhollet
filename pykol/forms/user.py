# -*- coding: utf-8 -*-

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

"""
Formulaires pour manipuler les données des comptes utilisateurs.
"""

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

from pykol.models.base import Professeur, Etudiant
User = get_user_model()
from .permissions import ColloscopePermFormSet

class MonProfilForm(forms.ModelForm):
	"""
	Formulaire d'édition des informations utilisateur, destiné à être
	utilisé par l'utilisateur lui-même.
	"""
	prefix = 'profil'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['email'].disabled = True

	class Meta:
		model = User
		fields = ('email',)

class MonProfilPasswordForm(PasswordChangeForm):
	"""
	Changement de mot de passe par l'utilisateur lui-même.
	"""
	prefix = 'pass'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['new_password1'].required = False
		self.fields['new_password2'].required = False
		self.fields['old_password'].required = False

	def clean_new_password2(self):
		password1 = self.cleaned_data.get('new_password1')
		password2 = self.cleaned_data.get('new_password2')
		if password1 or password2:
			return super().clean_new_password2()
		return None

	def save(self, commit=True):
		if self.cleaned_data.get('new_password2'):
			super().save(commit)
		return self.user

class UserForm(forms.ModelForm):
	"""
	Édition complète du profil d'un utilisateur.
	"""
	prefix = 'user'

	class Meta:
		model = User
		fields = ('last_name', 'first_name', 'email', 'sexe',
				'birth_date',)

class ProfesseurForm(forms.ModelForm):
	"""
	Édition des informations spécifiques aux professeurs.
	"""
	prefix = 'prof'

	class Meta:
		model = Professeur
		fields = ('corps', 'etablissement', 'id_acad',
				'nom_asie', 'prenom_asie')

class EtudiantForm(forms.ModelForm):
	"""
	Édition des informations spécifiques aux étudiants.
	"""
	prefix = 'etudiant'

	class Meta:
		model = Etudiant
		fields = ('ine', 'classe', 'origine', 'entree', 'sortie',)

class FullUserForm(forms.Form):
	"""
	Formulaire d'édition d'un compte utilisateur.

	PyKol possède les modèles User, Professeur et Etudiant. Professeur
	et Etudiant héritent (multi-table) de User. Ce formulaire possède
	un bouton radio permettant de choisir quelle catégorie d'utilisateur
	il faut créer. Il propose trois sous-formulaires :
	- self.user_form est un UserForm qui permet d'éditer les
	  informations communes aux trois profils ;
	- self.prof_form est un ProfesseurForm qui permet de remplir les
	  informations spécifiques à un professeur ;
	- self.etu_form est un EtudiantForm qui permet de remplir les
	  informations spécifiques à un étudiant.

	Le champ categorie n'est modifiable que lorsque l'on crée un nouvel
	utilisateur (changer le type d'utilisateur est une plaie avec
	Django, donc ce n'est pas encore implémenté).
	"""
	CATEGORIE_BASE = 0
	CATEGORIE_PROF = 1
	CATEGORIE_ETUDIANT = 2
	CATEGORIE_CHOICES = (
		(CATEGORIE_BASE, "Utilisateur simple"),
		(CATEGORIE_PROF, "Professeur"),
		(CATEGORIE_ETUDIANT, "Étudiant"),
	)
	categorie = forms.TypedChoiceField(choices=CATEGORIE_CHOICES,
			coerce=int,
			initial=CATEGORIE_PROF, widget=forms.RadioSelect)

	@staticmethod
	def _unrequire_fields(form):
		"""
		Mettre required=False sur tous les champs d'un formulaire.
		"""
		for field_name in form.fields:
			form.fields[field_name].required = False

	def __init__(self, *args, instance=None, initial={}, **kwargs):
		self.instance = instance

		dash = '-' if self.prefix is not None else ''
		pfx = self.prefix if self.prefix else ''
		user_prefix = '{pfx}{dash}{mypfx}'.format(pfx=pfx, dash=dash, mypfx='user')
		prof_prefix = '{pfx}{dash}{mypfx}'.format(pfx=pfx, dash=dash, mypfx='prof')
		etu_prefix  = '{pfx}{dash}{mypfx}'.format(pfx=pfx, dash=dash, mypfx='etu')

		self.user_form = UserForm(*args, prefix=user_prefix, instance=instance)

		if instance is None:
			self.prof_form = ProfesseurForm(*args, prefix=prof_prefix)
			self.etu_form = EtudiantForm(*args, prefix=etu_prefix)

			self._unrequire_fields(self.prof_form)
			self._unrequire_fields(self.etu_form)
		else:
			initial['categorie'] = FullUserForm.CATEGORIE_BASE

			try:
				self.prof_form = ProfesseurForm(*args, prefix=prof_prefix,
						instance=instance.professeur)
				initial['categorie'] = FullUserForm.CATEGORIE_PROF
			except:
				self.prof_form = ProfesseurForm(*args, prefix=prof_prefix)

			try:
				self.etu_form = EtudiantForm(*args, prefix=etu_prefix,
						instance=instance.etudiant)
				initial['categorie'] = FullUserForm.CATEGORIE_ETUDIANT
			except:
				self.etu_form = EtudiantForm(*args, prefix=etu_prefix)

		super().__init__(*args, initial=initial, **kwargs)

		# On ne peut choisir le type d'utilisateur qu'à la création
		if instance is not None:
			self.fields['categorie'].readonly = True

	def is_valid(self):
		if not (super().is_valid() and self.user_form.is_valid()):
			return False

		if self.is_professeur():
			return self.prof_form.is_valid()

		if self.is_etudiant():
			return self.etu_form.is_valid()

		return True

	def full_clean(self):
		super().full_clean()

		if not self.is_bound:
			return

		self.user_form.full_clean()

		if 'categorie' in self.cleaned_data:
			if self.is_professeur():
				self.prof_form.full_clean()

			if self.is_etudiant():
				self.etu_form.full_clean()

	def is_professeur(self):
		if self.instance is not None:
			return hasattr(self.instance, 'professeur')
		return self.cleaned_data['categorie'] == FullUserForm.CATEGORIE_PROF

	def is_etudiant(self):
		if self.instance is not None:
			return hasattr(self.instance, 'etudiant')
		return self.cleaned_data['categorie'] == FullUserForm.CATEGORIE_ETUDIANT

	def save(self, commit=True):
		# On commence par créer l'objet User de base. Ce n'est pas
		# nécessairement lui qui sera vraiment stocké dans la base, mais
		# peut-être l'une des sous-classes Professeur ou Etudiant.
		# Cet objet de base permettra alors de recopier rapidement les
		# champs.
		res = self.user_form.save(commit=False)

		if self.is_professeur():
			prof = self.prof_form.save(commit=False)
			prof.__dict__.update(res.__dict__)
			res = prof

		if self.is_etudiant():
			etu = self.etu_form.save(commit=False)
			etu.__dict__.update(res.__dict__)
			res = etu

		if commit:
			res.save()

		return res

class ColleursImportForm(forms.Form):
	"""
	Formulaire d'import d'un fichier OpenDocument listant les colleurs
	extérieurs.
	"""
	colleurs = forms.FileField(widget=forms.ClearableFileInput(
		attrs={'accept': 'application/vnd.oasis.opendocument.spreadsheet'}))
	mise_a_jour = forms.BooleanField(label="Mise à jour sans ajout",
			required=False, initial=False)
