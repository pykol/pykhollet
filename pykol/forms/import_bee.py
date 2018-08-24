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

from pykol.models.base import Annee

class ImportBEEForm(forms.Form):
	annee = forms.ModelChoiceField(queryset=Annee.objects.order_by('debut'),
			required=False, label="Année scolaire",
			initial=Annee.objects.get_actuelle)
	nomenclature = forms.FileField(required=False)
	structure = forms.FileField(required=False)
	eleves = forms.FileField(required=False)
	stsemp = forms.FileField(required=False)

	def clean(self):
		"""
		On vérifie que l'on peut déterminer l'année scolaire, soit avec
		le champ annee du formulaire, soit parce que l'export stsemp a
		été fourni.

		L'année scolaire n'est nécessaire que si l'on importe les
		fichiers Structure ou Eleves.
		"""
		cleaned_data = super().clean()

		if not cleaned_data.get('annee') and not cleaned_data.get('stsemp') \
			and (cleaned_data.get('structure') or
					cleaned_data.get('eleves')):
			raise forms.ValidationError(
					"Vous devez indiquer à quelle année scolaire "
					"correspondent les données que vous souhaitez "
					"importer, soit en indiquant explicitement l'année "
					"soit en ajoutant l'export STS (qui contient "
					"l'année).")

		return cleaned_data
