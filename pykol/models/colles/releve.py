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


"""Modèles pour la gestion des relevés des heures de colles
effectuées et leur mise en paiement."""

from django.db import models, transaction
from django.utils.timezone import localtime

class ColleReleve(models.Model):
	date = models.DateTimeField()
	date_paiement = models.DateTimeField(blank=True, null=True)

	ETAT_NOUVEAU = 0
	ETAT_PAYE = 1
	ETAT_CHOICES = (
			(ETAT_NOUVEAU, 0),
			(ETAT_PAYE, 1),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=0)

	@transaction.atomic
	def payer(self, date=None):
		if date is None:
			self.date_paiement = localtime()
		else:
			self.date_paiement = date
		self.etat = ColleReleve.ETAT_PAYE
		self.save()

	class Meta:
		verbose_name = "relevé des colles"
		verbose_name_plural = "relevés des colles"
