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
from django.forms import formset_factory, modelformset_factory, \
		inlineformset_factory

from pykol.models.base import Matiere, Etudiant
from pykol.models.colles import Semaine, CollesReglages, Creneau, \
		Roulement, RoulementLigne, RoulementApplication, \
		RoulementGraineLigne
from pykol.forms import CommaSeparatedCharField

class SemaineForm(forms.Form):
	debut = forms.DateField(label="début")
	fin = forms.DateField(label="fin")
	est_colle = forms.BooleanField(label="semaine de colle",
			required=False)
	numero = forms.CharField(label="numéro", required=False)
	semaine = forms.ModelChoiceField(queryset=Semaine.objects,
			widget=forms.HiddenInput, required=False)

	def __init__(self, *args, classe=None, **kwargs):
		super().__init__(*args, **kwargs)
		if classe:
			self.fields['semaine'].queryset = Semaine.objects.filter(classe=classe)

	def clean(self):
		cleaned_data = super().clean()
		if cleaned_data.get('est_colle') and not cleaned_data.get('numero'):
			raise forms.ValidationError(
					"Il faut obligatoirement donner un numéro à chaque "
					"semaine de colle.")

SemaineFormSet = formset_factory(SemaineForm, extra=0)

class SemaineNumeroGenerateurForm(forms.ModelForm):
	class Meta:
		model = CollesReglages
		fields = ('numeros_auto', 'numeros_format',)

class CreneauForm(forms.ModelForm):
	def __init__(self, *args, classe=None, **kwargs):
		super().__init__(*args, **kwargs)
		if classe:
			self.fields['matiere'].queryset = Matiere.objects.filter(enseignement__classe=classe)

	class Meta:
		model = Creneau
		fields = ('classe', 'jour', 'debut', 'fin', 'salle', 'colleur',
				'matiere',)

CreneauFormSet = modelformset_factory(Creneau, form=CreneauForm,
		can_delete=True, extra=0, fields=CreneauForm.Meta.fields)

CreneauSansClasseFormSet = modelformset_factory(Creneau,
		form=CreneauForm, can_delete=True, extra=3,
		fields = ('jour', 'debut', 'fin', 'salle', 'colleur',
			'matiere',))

class LabelledHiddenWidget(forms.HiddenInput):
	def __init__(self, *args, **kwargs):
		super(LabelledHiddenWidget, self).__init__(*args, **kwargs)

	def render(self, name, value, attrs=None):
		input_html = super(LabelledHiddenWidget, self).render(name, value, attrs)
		for pk, val in self.choices:
			if pk == value:
				input_html += val
				break
		return input_html

class TrinomeForm(forms.Form):
	etudiant = forms.ModelChoiceField(required=True,
			queryset=Etudiant.objects.none(),
			widget=LabelledHiddenWidget())
	groupes = CommaSeparatedCharField(required=False)

	def __init__(self, *args, queryset=None, **kwargs):
		super().__init__(*args, **kwargs)
		if queryset is not None:
			self.fields['etudiant'].queryset = queryset

class RoulementApplicationForm(forms.ModelForm):
	class Meta:
		model = RoulementApplication
		fields = ('semaines',)

RoulementLigneFormSet = forms.inlineformset_factory(Roulement,
		RoulementLigne, fields=('ordre', 'creneau',), can_delete=True)

RoulementGraineFormSet = forms.inlineformset_factory(RoulementApplication,
		RoulementGraineLigne, fields=('trinome', 'decalage'))
