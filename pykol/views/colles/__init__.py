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

from .colloscope import colloscope_home
from .colloscope import creneaux, creneau_list_direction
from .colloscope import colle_creer, colle_supprimer

from .colles import colle_declarer, colle_deplacer, \
		colle_list, colle_annuler, colle_a_noter_list, \
		colle_detail

from .decompte import decompte_list, decompte_detail, \
		decompte_creer

from .resultats import classe_resultats

from .periodenotation import periode_notation

from .calendrier import calendrier
