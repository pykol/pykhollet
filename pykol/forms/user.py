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
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth.forms import PasswordChangeForm

from pykol.models.base import User, Professeur, Etudiant

class MonProfilForm(forms.ModelForm):
	prefix = 'profil'

	class Meta:
		model = User
		fields = ('email', )

class MonProfilPasswordForm(PasswordChangeForm):
	prefix = 'pass'

class FullUserForm(forms.ModelForm):
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
