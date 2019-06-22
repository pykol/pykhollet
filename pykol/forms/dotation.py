# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
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

from django.forms import Form

from pykol.models.comptabilite import Compte, Mouvement
from pykol.models.base import Annee

class BaseVirementForm(Form):
	"""
	Formulaire de base pour créer un virement d'heures d'un compte à un
	autre.

	Les comptes source et destination doivent être renvoyés par des
	méthodes get_compte_source et get_compte_destination.
	"""
	duree = forms.DurationField(label="durée")
	motif = forms.CharField(max_length=Mouvement._meta.get_field('motif').max_length)
	annee = forms.ModelChoiceField(queryset=Annee.objects.all)

	def get_compte_source(self):
		"""
		Obtention du compte source pour le virement.

		Cette méthode est appelée par la méthode save() et doit être
		implémentée manuellement.
		"""
		raise NotImplemented

	def get_compte_destination(self):
		"""
		Obtention du compte destination pour le virement.

		Cette méthode est appelée par la méthode save() et doit être
		implémentée manuellement.
		"""
		raise NotImplemented

	def save(self):
		"""
		Crée et valide le virement.

		Cette méthode peut lever l'exception
		pykol.models.comptabilite.CompteDecouvert si le solde du compte
		source ne permet pas de créer ce virement.
		"""
		Mouvement.objects.virement(
			compte_debit=self.get_compte_source(),
			compte_credit=self.get_compte_destination(),
			duree=self.cleaned_data['duree'],
			duree_interrogation=self.cleaned_data['duree'],
			motif=self.cleaned_data['motif'],
			annee=self.cleaned_data['annee']).valider()

class VirementSourceForm(BaseVirementForm):
	"""
	Virement où le choix du compte source est fourni par un composant de
	formulaire.
	"""
	source = forms.ModelChoiceField(queryset=Compte.objects.all,
			label="compte source")

	def __init__(self, *args, **kwargs):
		source_qs = kwargs.pop('source_qs', Compte.objects.all)
		super().__init__(*args, **kwargs)
		self.fields['source'].queryset = source_qs

	def get_compte_source(self):
		return self.cleaned_data['source']

class VirementDestinationForm(BaseVirementForm):
	"""
	Virement où le choix du compte destination est fourni par un composant de
	formulaire.
	"""
	destination = forms.ModelChoiceField(queryset=Compte.objects.all,
			label="compte destination")

	def __init__(self, *args, **kwargs):
		destination_qs = kwargs.pop('destination_qs', Compte.objects.all)
		super().__init__(*args, **kwargs)
		self.fields['destination'].queryset = destination_qs

	def get_compte_destination(self):
		return self.cleaned_data['destination']

class VirementForm(VirementSourceForm, VirementDestinationForm):
	"""
	Formulaire de virement générique.
	"""
	pass

class VirementClasseMatiereForm(VirementDestinationForm):
	"""
	Formulaire pour ajouter des heures à une matière dans une classe. 
	"""
	pass
