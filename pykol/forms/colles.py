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

from pykol.models.colles import Colle, ColleNote
from . import LabelledHiddenWidget

class ColleNoteForm(forms.ModelForm):
	class Meta:
		model = ColleNote
		fields = ('eleve', 'horaire', 'note')
		widgets = {
			'eleve': LabelledHiddenWidget,
		}

ColleNoteFormSet = forms.inlineformset_factory(Colle, ColleNote,
		form=ColleNoteForm,
		fields=('eleve', 'horaire', 'note'), can_delete=False)
