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

from .jury import jury_list, jury_detail, jury_creer, jury_supprimer, \
		jury_detail_etudiant, jury_retirer_etudiant, \
		jury_mentions_orphelines
from .attestations import jury_toutes_attestations_resultats, \
		jury_attestation_etudiant, jury_toutes_attestations_parcours
from .grille import grilles_charger
