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
	Renvoie une redirection HTTP vers l'URL donnée (par ordre de
	préférence, les valeurs non définies sont ignorées) par :
	1. la valeur de request.POST['next'] ;
	2. la valeur de request.GET['next'] ;
	3. ou par défaut la valeur du paramètre 'to'.

	La valeur de 'to' peut être n'importe quelle valeur acceptée par la
	fonction django.shortcuts.to. Aucune vérification n'est effectuée
	sur cette valeur.

	Les valeurs de request.POST['next'] ou de request.GET['next'] sont
	testées avant de réaliser la redirection, afin de savoir s'il s'agit
	d'une URL sécurisée pour une redirection.
	"""
	try:
		if is_safe_url(request.POST['next'], allowed_hosts=None):
			return redirect(request.POST['next'], *args, **kwargs)
	except:
		pass

	try:
		if is_safe_url(request.GET['next'], allowed_hosts=None):
			return redirect(request.GET['next'], *args, **kwargs)
	except:
		pass

	return redirect(to, *args, **kwargs)
