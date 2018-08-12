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

"""Raccourcis pratiques et fréquemment utilisés dans pyKol"""

from django.shortcuts import redirect
from django.utils.http import is_safe_url

def redirect_next(to, *args, request=None, **kwargs):
	"""
	Redirection vers la valeur de request.POST['next'] si cette valeur
	est définie, ou bien vers 'to' par défaut sinon.

	La valeur de 'to' peut être n'importe quelle valeur acceptée par la
	fonction django.shortcuts.to.

	La valeur de request.POST['next'] est testée avant de réaliser la
	redirection afin de savoir s'il s'agit d'une URL sécurisée pour une
	redirection.
	"""
	if request is not None and \
			'next' in request.POST and \
			is_safe_url(request.POST['next']):
		return redirect(request.POST['next'], *args, **kwargs)
	else:
		return redirect(to, *args, **kwargs)
