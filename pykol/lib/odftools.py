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
from odf.table import TableCell

def concat_text_nodes(element):
	res = ""
	for child in element.childNodes:
		if child.nodeType == child.TEXT_NODE:
			res += child.data
		elif child.nodeType == child.ELEMENT_NODE:
			res += concat_text_nodes(child)
	return res

def tablecell_to_text(cell):
	"""
	Récupère le contenu textuel d'une case d'un tableau
	"""
	return "".join([concat_text_nodes(par)
		for par in cell.getElementsByType(P)])

def iter_columns(row):
	"""
	Itérateur sur les colonnes d'une ligne d'un tableau, en prenant en
	compte les colonnes répétées implicitement avec l'attribut
	number-columns-repeated.
	"""
	cells = row.getElementsByType(TableCell)
	for cell in cells:
		repeat = cell.getAttribute('numbercolumnsrepeated') or 1
		for i in range(repeat):
			yield(cell)
