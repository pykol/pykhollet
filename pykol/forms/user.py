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

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

from pykol.models.base import Professeur, Etudiant
User = get_user_model()
from .permissions import ColloscopePermFormSet

class MonProfilForm(forms.ModelForm):
	prefix = 'profil'

	class Meta:
		model = User
		fields = ('email', )

class MonProfilPasswordForm(PasswordChangeForm):
	prefix = 'pass'

class UserForm(forms.ModelForm):
	prefix = 'user'

	class Meta:
		model = User
		fields = ('last_name', 'first_name', 'email', 'sexe',)

class ProfesseurForm(forms.ModelForm):
	prefix = 'prof'

	class Meta:
		model = Professeur
		fields = ('corps', 'etablissement',)

class EtudiantForm(forms.ModelForm):
	prefix = 'etudiant'

	class Meta:
		model = Etudiant
		fields = ('ine', 'classe', 'origine', 'entree', 'sortie',)

class FullUserForm(forms.Form):
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

		if instance is not None:
			self.fields['categorie'].readonly = True

	def is_valid(self):
		if not (super().is_valid() and self.user_form.is_valid()):
			return False

		if self.is_professeur():
			return self.prof_form.is_valid()

		if self.is_etudiant():
			return self.etu_form.is_valid()

	def full_clean(self):
		super().full_clean()

		self.user_form.full_clean()

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
		res = self.user_form.save(commit=False)

		if self.is_professeur():
			prof = self.prof_form.save(commit=False)
			prof.__dict__.update(res.__dict__)
			res = prof

		if self.is_etudiant():
			etu = self.etu_form.save(commit=False)
			etu.__dict__.update(res.__dict__)
			res = etu

		res.save()

		return res
