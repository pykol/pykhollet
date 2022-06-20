# -*- coding:utf8 -*-

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

"""
Constantes utilisées un peu partout dans le code
"""

# Nombre de semaines constituant la première période de l'année
# Fixé par l'arrêté du 10 février 1995 (RESK9500109A)
SEMAINES_PREMIERE_PERIODE = 18

# Valeurs pour les choix des périodes
PERIODE_ANNEE = 0
PERIODE_PREMIERE = 1
PERIODE_DEUXIEME = 2
PERIODE_XOR_CHOICES = (
		(PERIODE_PREMIERE, 'première période'),
		(PERIODE_DEUXIEME, 'deuxième période'),
	)
PERIODE_CHOICES = (
		(PERIODE_ANNEE, 'année complète'),
    ) + PERIODE_XOR_CHOICES
