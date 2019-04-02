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
from django.forms import inlineformset_factory, RadioSelect, \
		modelformset_factory, HiddenInput

from pykol.models.ects import Jury, Mention

MentionFormSet = inlineformset_factory(Jury, Mention,
		fields=('mention',), can_delete=False, extra=0,
		widgets={
			'mention': RadioSelect(),
		})

class MentionGlobaleForm(forms.ModelForm):
	class Meta:
		model = Mention
		fields = ('jury', 'etudiant', 'mention', 'credits',)
		widgets = {
			'mention': RadioSelect(),
			'etudiant': HiddenInput(),
			'jury': HiddenInput(),
			'credits': HiddenInput(),
		}
	def save(self, commit=True):
		super().save(commit=False)
		self.instance.globale = True
		if commit:
			self.instance.save()

class JuryForm(forms.ModelForm):
	class Meta:
		model = Jury
		fields = ('classe', 'date', 'periode',)

class JuryDateForm(forms.ModelForm):
	class Meta:
		model = Jury
		fields = ('date',)
