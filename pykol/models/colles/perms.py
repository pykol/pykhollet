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
Module des gestion des permissions sur les colloscopes

La gestion des permissions sur les colloscopes n'est pas globale
(contrairement au modèle standard de permissions de Django), mais
se fait classe par classe et utilisateur par utilisateur.

Il est possible d'accorder à un utilisateur donné dans une classe donnée
le droit de modifier tout le colloscope, ou celui de modifier uniquement
les colles de sa propre matière.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from pykol.models.base import Classe

class ColloscopePermission(models.Model):
	"""Gestion des permissions d'édition des colloscopes

	Ce modèle permet de définir classe par classe et pour chaque
	professeur quels sont les droits dont il dispose pour modifier le
	colloscope.

	Les professeurs qui interviennent dans une classe peuvent toujours
	consulter le colloscope de la classe. Il est cependant possible de
	donner les droits de lecture sur un colloscope à un professeur
	extérieur à la classe.
	"""
	def droit_choices():
		return {'content_type':
				ContentType.objects.get_for_model(Classe)}
	user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
			verbose_name="utilisateur")
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	matiere_seulement = models.BooleanField(verbose_name="Restreindre à"
			" sa matière")
	droit = models.ForeignKey(Permission, on_delete=models.CASCADE,
			limit_choices_to=droit_choices)

	class Meta:
		verbose_name = "permission sur le colloscope"
		verbose_name_plural = "permissions sur le colloscope"
