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

from datetime import timedelta
from collections import Counter

from django import forms
from django.forms import formset_factory, modelformset_factory, \
		inlineformset_factory

from pykol.models.base import Matiere, Etudiant, Professeur, \
		Enseignement, Annee
from pykol.models.colles import Semaine, CollesReglages, Creneau, \
		Roulement, RoulementLigne, RoulementApplication, \
		RoulementGraineLigne, Colle, Trinome, CollesEnseignement
from pykol.forms import CommaSeparatedCharField, LabelledHiddenWidget

class EnseignementDoteMixin(forms.Form):

	def _coerce_enseignement_dote(value):
		"""
		Transforme une chaine de la forme "pk_ens-pk_ce" où pk_ens et
		pk_ce sont des entiers en un dictionnaire qui donne les objets
		Enseignement et CollesEnseignement de clés primaires respecties
		pk_ens et pk_ce.
		"""
		pks = [int(v) for v in value.split("-")]
		ens = Enseignement.objects.get(pk=pks[0])
		collesens = CollesEnseignement.objects.get(pk=pks[1])
		return {'enseignement': ens, 'collesenseignement': collesens}

	# Les choix possibles pour ce champ sont initialisés d'après la
	# classe donnée dans __init__.
	enseignement_dote = forms.TypedChoiceField(
			label="Matière",
			coerce=_coerce_enseignement_dote,
			empty_value={'enseignement': None, 'collesenseignement': None},
			initial='')

	def __init__(self, *args, classe=None, **kwargs):
		super().__init__(*args, **kwargs)

		if classe:
			# Une colle est affectée non seulement à un enseignement, mais
			# est prise sur une dotation. La plupart du temps, il n'existe
			# qu'une seule dotation pour un enseignement donné. Cependant,
			# en ECE/ECS, un même enseignement peut recevoir plusieurs
			# dotations de colles (dotation pour les mathématiques et
			# dotation pour l'informatique, attribuées au même code
			# matière).
			# On construit la liste des enseignements, éventuellement
			# multipliés par les dotations correspondantes.
			enseignements = Enseignement.objects.filter(
					classe=classe,
					collesenseignement__classe=classe)
		else:
			enseignements = Enseignement.objects.filter(classe__annee=Annee.objects.get_actuelle())

		enseignements = enseignements.values(
				'pk',
				'collesenseignement__pk',
				'matiere__nom',
				'groupe__nom',
				'matiere__parent__nom',
				'collesenseignement__nom').order_by(
						'collesenseignement',
						'matiere__nom',
						'groupe__nom',
					)

		choix = [('', '---------')]

		# Le dictionnaire compte_matieres sert à déterminer les
		# matières qui apparaissent plus d'une fois dans la liste.
		# Dans ce cas, on affiche le nom du groupe pour désambigüer.
		compte_matieres = Counter([e['matiere__nom'] for e in
			enseignements])
		for enseignement in enseignements:
			nom_format = '{matiere__nom}'

			if not classe or (enseignement['groupe__nom'] != classe.nom and \
					compte_matieres[enseignement['matiere__nom']] > 1):
				nom_format += ' {groupe__nom}'

			if enseignement['collesenseignement__nom']:
				nom_format += ' ({collesenseignement__nom})'
			elif enseignement['matiere__parent__nom']:
				nom_format += ' ({matiere__parent__nom})'

			nom_dotation = nom_format.format(**enseignement)

			choix.append(
					(
						'{pk}-{collesenseignement__pk}'.format(**enseignement),
						nom_dotation,
					)
				)

		self.fields['enseignement_dote'].choices = choix

class ColleForm(EnseignementDoteMixin, forms.Form):
	"""
	Formulaire de création d'une colle
	"""
	colleur = forms.ModelChoiceField(
			queryset=Professeur.objects.order_by('last_name',
				'first_name'))
	salle = forms.CharField(max_length=30, required=False)

	mode = forms.TypedChoiceField(label="Mode de déroulement",
			choices=Colle.MODE_CHOICES,
			initial=Colle.MODE_INTERROGATION, coerce=int,
			widget=forms.RadioSelect())

	creneau = forms.ModelChoiceField(queryset=None, required=False)
	semaine = forms.ModelChoiceField(queryset=None, required=False)
	horaire = forms.DateTimeField(required=False)
	duree = forms.DurationField(required=False,
			initial=timedelta(hours=1))

	trinome = forms.ModelChoiceField(queryset=None, required=False)
	etudiants = forms.ModelMultipleChoiceField(queryset=None,
			required=False, widget=forms.CheckboxSelectMultiple)

	def __init__(self, *args, classe, **kwargs):
		super().__init__(*args, classe=classe, **kwargs)

		self.fields['creneau'].queryset = Creneau.objects.filter(classe=classe).order_by(
				'enseignement', 'colleur', 'jour')
		self.fields['semaine'].queryset = Semaine.objects.filter(classe=classe).order_by('debut')
		self.fields['trinome'].queryset = Trinome.objects.filter(classe=classe).order_by('nom')
		self.fields['etudiants'].queryset = classe.etudiants.order_by('last_name', 'first_name')

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

class CreneauForm(EnseignementDoteMixin, forms.ModelForm):
	# On change le format par défaut pour accepter des heures simples
	debut = forms.TimeField(label="Début", input_formats=('%H', '%H:%M', '%H:%M:%S'))
	fin   = forms.TimeField(label="Fin",   input_formats=('%H', '%H:%M', '%H:%M:%S'))

	class Meta:
		model = Creneau
		fields = ('classe', 'jour', 'debut', 'fin', 'salle', 'colleur',)

	def __init__(self, *args, classe=None, **kwargs):
		super().__init__(*args, classe=classe, **kwargs)

		self.fields['colleur'].queryset = Professeur.objects.order_by(
				'last_name', 'first_name')

		if kwargs.get('instance') is not None:
			self.fields['enseignement_dote'].initial = "{}-{}".format(
					self.instance.enseignement.pk,
					self.instance.colles_ens.pk)

	def save(self, commit=True):
		creneau = super().save(commit=False)
		creneau.enseignement = self.cleaned_data.get('enseignement_dote')['enseignement']
		creneau.colles_ens   = self.cleaned_data.get('enseignement_dote')['collesenseignement']

		if commit:
			creneau.save()

		return creneau

CreneauFormSet = modelformset_factory(Creneau, form=CreneauForm,
		can_delete=True, extra=0, fields=CreneauForm.Meta.fields)

CreneauSansClasseFormSet = modelformset_factory(Creneau,
		form=CreneauForm, can_delete=True, extra=3,
		fields = ('jour', 'debut', 'fin', 'salle', 'colleur',
			))

class TrinomeForm(forms.Form):
	etudiant = forms.ModelChoiceField(required=True,
			queryset=Etudiant.objects.none(),
			widget=LabelledHiddenWidget())
	groupes = CommaSeparatedCharField(required=False)
	groupes_periode_premiere = CommaSeparatedCharField(required=False)
	groupes_periode_deuxieme = CommaSeparatedCharField(required=False)

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

class ColleSupprimerForm(forms.ModelForm):
	"""
	Formulaire qui référence une colle mais sans permettre la
	modification du moindre champ. Il permet de gérer la confirmation de
	suppression d'une colle.
	"""
	class Meta:
		model = Colle
		fields = ()


class ColloscopeImportForm(forms.Form):
	colloscope_ods = forms.FileField()
	supprimer = forms.BooleanField(required=False)
