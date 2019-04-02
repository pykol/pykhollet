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
	"""
	Formulaire de création d'un jury ECTS par la direction.
	"""
	class Meta:
		model = Jury
		fields = ('classe', 'date', 'periode',)

class JuryDateForm(forms.ModelForm):
	"""
	Formulaire de modification de la date d'un jury.
	"""
	class Meta:
		model = Jury
		fields = ('date',)

class JuryTerminerForm(forms.ModelForm):
	"""
	Formulaire de clôture d'un jury ECTS.

	Ce formulaire ne contient aucun champ, il permet simplement de
	changer l'état du jury en "terminé" lorsqu'il est enregistré.
	"""
	class Meta:
		model = Jury
		fields = tuple()

	def save(self, commit=True):
		"""
		Cette méthode sauvegarde l'instance de Jury désignée par ce
		formulaire et change l'état en Jury.ETAT_TERMINE.
		"""
		super().save(commit=False)
		self.instance.etat = Jury.ETAT_TERMINE
		if commit:
			self.instance.save()
