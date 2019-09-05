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

from django.forms import inlineformset_factory, ModelChoiceField

from pykol.models.colles import ColloscopePermission
from pykol.models.base import Professeur

class DroitField(ModelChoiceField):
	def label_from_instance(self, droit):
		return droit.name

class ClasseField(ModelChoiceField):
	def label_from_instance(self, classe):
		return "{annee} − {nom}".format(annee=classe.annee,
				nom=classe.nom)

ColloscopePermFormSet = inlineformset_factory(
		Professeur, ColloscopePermission, fields=('classe',
			'matiere_seulement', 'droit'), can_delete=True,
		field_classes = {'classe': ClasseField, 'droit': DroitField})
