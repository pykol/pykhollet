# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
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

import io
from django.views.generic.base import ContextMixin
from django.shortcuts import render
from django.http import HttpResponse

from pykol.models.comptabilite import CompteDecouvert

class CompteDecouvertMixin(ContextMixin):
	"""
	Mixin pour attraper l'exception CompteDecouvert dans une vue.
	"""
	decouvert_template = 'pykol/comptabilite/decouvert.html'

	def dispatch(self, *args, **kwargs):
		try:
			return super().dispatch(*args, **kwargs)
		except CompteDecouvert:
			# Renvoyer un message d'erreur générique lorsque l'opération
			# a échoué à cause d'un découvert non autorisé.
			return render(request, self.decouvert_template,
					context=self.get_context_data())

class OdfResponse(HttpResponse):
	"""
	Classe générique pour aider à construire une réponse au format
	OpenDocument.
	"""
	def __init__(self, opendocument, **kwargs):
		self.filename = kwargs.pop('filename', None)
		self.opendocument = opendocument
		kwargs.setdefault('content_type', self.opendocument.getMediaType())
		super().__init__(**kwargs)
		buffer = io.BytesIO()
		self.opendocument.save(buffer)
		self.write(buffer.getvalue())
		if self.filename is not None:
			self['Content-Disposition'] = 'attachment; filename="{}"'.format(self.filename)
		self.opendocument.write(self)
