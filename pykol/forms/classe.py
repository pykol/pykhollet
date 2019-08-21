# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018-2019 Florian Hatat
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

from django.forms import ModelForm, modelformset_factory, \
		ModelChoiceField

from pykol.models.base import Service

class EnseignementSansClasseField(ModelChoiceField):
	"""
	Classe qui permet de personnaliser les libellés des enseignements
	affichés par les instances de ServiceForm.
	"""
	def label_from_instance(self, obj):
		return str(obj.matiere)

class ServiceForm(ModelForm):
	"""
	Formulaire qui permet d'éditer un objet Service afin de modifier le
	professeur et l'enseignement.
	"""
	def __init__(self, *args, **kwargs):
		classe_qs = kwargs.pop('classe_qs', None)
		super().__init__(*args, **kwargs)
		if classe_qs is not None:
			self.fields['enseignement'].queryset = classe_qs.enseignements

	class Meta:
		model = Service
		fields = ('professeur', 'enseignement',)
		field_classes = {
			'enseignement': EnseignementSansClasseField,
		}

ServiceFormset = modelformset_factory(Service, form=ServiceForm,
		can_delete=True, extra=3, fields=ServiceForm.Meta.fields)
