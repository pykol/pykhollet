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

import os

from django.core.files.storage import FileSystemStorage
from django.conf import settings

class PrivateFileSystemStorage(FileSystemStorage):
	def __init__(self, *args, **kwargs):
		kwargs['location'] = os.path.abspath(settings.PYKOL_PRIVATE_MEDIA_ROOT)
		super().__init__(*args, **kwargs)

private_storage = PrivateFileSystemStorage()
