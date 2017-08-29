# -*- coding: utf-8 -*-

from django import forms
from django.forms import formset_factory

from colles.models import Semaine, CollesReglages

class SemaineForm(forms.Form):
	debut = forms.DateField(label="début")
	fin = forms.DateField(label="fin")
	est_colle = forms.BooleanField(label="semaine de colle",
			required=False)
	numero = forms.CharField(label="numéro", required=False)
	semaine = forms.ModelChoiceField(queryset=Semaine.objects,
			widget=forms.HiddenInput, required=False)

	def __init__(self, *args, classe=None, **kwargs):
		super(SemaineForm, self).__init__(*args, **kwargs)
		if classe:
			self.fields['semaine'].queryset = Semaine.objects.filter(classe=classe)

	def clean(self):
		cleaned_data = super(SemaineForm, self).clean()
		if cleaned_data.get('est_colle') and not cleaned_data.get('numero'):
			raise forms.ValidationError(
					"Il faut obligatoirement donner un numéro à chaque "
					"semaine de colle.")

SemaineFormSet = formset_factory(SemaineForm, extra=0)

class SemaineNumeroGenerateurForm(forms.ModelForm):
	class Meta:
		model = CollesReglages
		fields = ('numeros_auto', 'numeros_format',)
