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
from django.utils import timezone

from pykol.models.base import Professeur, Enseignement
from pykol.models.colles import Colle, ColleNote, Trinome, \
		ColleDetails, PeriodeNotation
from . import LabelledHiddenWidget

class ColleNoteForm(forms.ModelForm):
	class Meta:
		model = ColleNote
		fields = ('eleve', 'note')
		widgets = {
			'eleve': LabelledHiddenWidget,
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['eleve'].disabled = True

	def save(self, commit=True):
		note = super().save(commit=False)
		if not note.horaire:
			note.horaire = timezone.now()
		if not note.duree:
			note.duree = note.colle.colles_ens.duree

		if commit:
			note.save()

		return note

ColleNoteFormSet = forms.inlineformset_factory(Colle, ColleNote,
		form=ColleNoteForm,
		fields=('eleve', 'note'), can_delete=False)

class ColleModifierForm(forms.Form):
	"""
	Formulaire de modification des détails d'une colle
	"""
	horaire = forms.DateTimeField(required=False)
	salle = forms.CharField(max_length=30, required=False)
	colleur = forms.ModelChoiceField(
			queryset=Professeur.objects.order_by('last_name',
				'first_name'), required=False)

	trinome = forms.ModelChoiceField(queryset=None, required=False)
	etudiants = forms.ModelMultipleChoiceField(queryset=None,
			required=False, widget=forms.CheckboxSelectMultiple)

	mode = forms.TypedChoiceField(label="Mode de déroulement",
			choices=Colle.MODE_CHOICES,
			coerce=int, empty_value=None,
			widget=forms.RadioSelect(), required=False)

	def __init__(self, *args, colle, **kwargs):
		etudiants_qs = kwargs.pop('etudiants', None) or \
			colle.classe.etudiants.order_by('last_name', 'first_name')
		super().__init__(*args, **kwargs)

		self.fields['trinome'].queryset = Trinome.objects.filter(classe=colle.classe).order_by('nom')
		self.fields['etudiants'].queryset = etudiants_qs.order_by('last_name', 'first_name')

ResaPonctuellesFormSet = forms.modelformset_factory(ColleDetails,
		fields=('salle',), can_delete=False)


class PeriodeNotationForm(forms.ModelForm):
	class Meta:
		model = PeriodeNotation
		fields = ('nom', 'debut', 'fin', 'enseignement',)

PeriodeNotationInlineFormset = forms.inlineformset_factory(Enseignement,
		PeriodeNotation,
		form=PeriodeNotationForm,
		fields=PeriodeNotationForm.Meta.fields,
		extra=1)

PeriodeNotationFormset = forms.modelformset_factory(
		PeriodeNotation,
		form=PeriodeNotationForm,
		fields=PeriodeNotationForm.Meta.fields,
		extra=1)
