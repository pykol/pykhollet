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

from pykol.models.base import Matiere, Etudiant, Professeur
from pykol.models.colles import Semaine, CollesReglages, Creneau, \
		Roulement, RoulementLigne, RoulementApplication, \
		RoulementGraineLigne, Colle, Trinome, CollesEnseignement
from pykol.forms import CommaSeparatedCharField
from . import LabelledHiddenWidget

class ColleForm(forms.Form):
	"""
	Formulaire de création d'une colle
	"""
	colleur = forms.ModelChoiceField(
			queryset=Professeur.objects.order_by('last_name',
				'first_name'))
	salle = forms.CharField(max_length=30, required=False)
	enseignement = forms.ModelChoiceField(queryset=None)

	creneau = forms.ModelChoiceField(queryset=None, required=False)
	semaine = forms.ModelChoiceField(queryset=None, required=False)
	horaire = forms.DateTimeField(required=False)

	trinome = forms.ModelChoiceField(queryset=None, required=False)
	etudiants = forms.ModelMultipleChoiceField(queryset=None,
			required=False, widget=forms.CheckboxSelectMultiple)

	def __init__(self, *args, classe, **kwargs):
		super().__init__(*args, **kwargs)

		self.fields['creneau'].queryset = Creneau.objects.filter(classe=classe).order_by(
				'matiere', 'colleur', 'jour')
		self.fields['semaine'].queryset = Semaine.objects.filter(classe=classe).order_by('debut')
		self.fields['trinome'].queryset = Trinome.objects.filter(dans_classe=classe).order_by('nom')
		self.fields['etudiants'].queryset = classe.etudiants.order_by('last_name', 'first_name')
		self.fields['enseignement'].queryset = CollesEnseignement.objects.filter(
				enseignement__classe=classe)

	def clean(self):
		cleaned_data = super().clean()

		# On vérifie que l'on peut bien déterminer l'heure, soit parce
		# que le créneau et la semaine ont été donnés, soit parce que
		# l'horaire a été donné.
		creneau = cleaned_data.get('creneau')
		semaine = cleaned_data.get('semaine')
		horaire = cleaned_data.get('horaire')

		erreurs = []

		if (creneau is not None and semaine is not None) == (horaire is not None):
			erreurs.append(forms.ValidationError(
					"Vous devez renseigner un horaire "
					"pour la colle, soit en indiquant un créneau et "
					"une semaine, soit en indiquant un horaire.",
					code='horaire_incorrect'))

		# On vérifie que l'on peut bien déterminer le groupe
		# d'étudiants, soit parce qu'un trinôme a été renseigné, soit
		# parce qu'une liste d'étudiants spécifique a été renseignée.
		trinome = cleaned_data.get('trinome')
		etudiants = cleaned_data.get('etudiants')
		if (trinome is None) != bool(etudiants):
			erreurs.append(forms.ValidationError(
				"Vous devez indiquer la liste des étudiants "
				"participant à la colle, soit en choisissant un "
				"trinôme de la classe, soit en sélectionnant "
				"manuellement les étudiants.",
				code='etudiants_inconnus'))

		if len(erreurs) > 0:
			if len(erreurs) > 1:
				raise forms.ValidationError(erreurs)
			else:
				raise erreurs[0]

		return cleaned_data

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
