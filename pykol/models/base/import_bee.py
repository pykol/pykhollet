# -*- coding:utf8 -*-

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

"""
Modèles pour garder un historique des importations de données
SIECLE et STS.
"""

from django.db import models
from .annee import Annee

class ImportBeeLog(models.Model):
	"""
	Ligne d'historique d'un import de données externe.
	"""
	date_fichier = models.DateField()
	date_import = models.DateField()
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE)

	IMPORT_TYPE_STS = 1
	IMPORT_TYPE_BASE_ELEVES = 2
	IMPORT_TYPE_STRUCTURES = 3
	IMPORT_TYPE_NOMENCLATURES = 4
	IMPORT_TYPE_COLLES = 5
	IMPORT_TYPE_GRILLES_ECTS = 6

	IMPORT_TYPE_CHOICES = (
		(IMPORT_TYPE_STS , "STS-EDT"),
		(IMPORT_TYPE_BASE_ELEVES , "base élèves"),
		(IMPORT_TYPE_STRUCTURES , "structures"),
		(IMPORT_TYPE_NOMENCLATURES , "nomenclatures"),
		(IMPORT_TYPE_COLLES , "dotations en colles"),
		(IMPORT_TYPE_GRILLES_ECTS , "grilles ECTS"),
	)
	import_type = models.PositiveSmallIntegerField(choices=IMPORT_TYPE_CHOICES)
