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

"""Fonctions utilitaires pour gérer les permissions des utilisateurs"""

from django.contrib.auth.backends import ModelBackend
from pykol.models.base import Classe
from pykol.models.colles import ColloscopePermission

class PykolBackend(ModelBackend):
	def get_user_permissions(self, user_obj, obj=None):
		return super().get_user_permissions(user_obj, obj)

	def get_group_permissions(self, user_obj, obj=None):
		return super().get_group_permissions(user_obj, obj)

	def get_all_permissions(self, user_obj, obj=None):
		if not user_obj.is_active or user_obj.is_anonymous:
			return set()

		if obj is None:
			return super().get_all_permissions(user_obj, obj)

		if isinstance(obj, Classe):
			# Permission de colloscope
			pass
		return set()
