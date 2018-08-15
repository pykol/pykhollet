# -*- coding: utf-8

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

"""Fonctions utilitaires pour manipuler les documents au format
OpenDocument."""

from odf.text import P

def tablecell_to_text(cell):
	"""
	Récupère le contenu textuel d'une case d'un tableau
	"""
	# TODO rechercher récursivement les TEXT_NODE, car il peut y avoir
	# d'autres enfants-éléments de P (par exemple des liens, de la mise
	# en forme dans des span, etc.).
	res = ""
	for par in cell.getElementsByType(P):
		res += "".join([t.data for t in par.childNodes
			if t.nodeType == t.TEXT_NODE])
	return res
