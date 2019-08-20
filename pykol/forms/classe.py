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

from django.forms import ModelForm, modelformset_factory

from pykol.models.base import Service

class ServiceForm(ModelForm):
	"""
	Formulaire qui permet d'éditer un objet Service afin de modifier le
	professeur et l'enseignement.
	"""
	def __init__(self, *args, **kwargs):
		classe = kwargs.pop('classe_qs')
		if classe is not None:
			self.fields['enseignement'].queryset = classe_qs.enseignements
	class Meta:
		model = Service
		fields = ('professeur', 'enseignement',)

ServiceFormset = modelformset_factory(Service, form=ServiceForm,
		can_delete=True, extra=3, fields=ServiceForm.Meta.fields)
