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

from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

from pykol.models.base import Classe

class ClasseDetailView(LoginRequiredMixin, generic.DetailView):
	model = Classe

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['etudiant_list'] = self.get_object().etudiant_set.order_by(
				'last_name', 'first_name')
		return context

class ClasseListView(LoginRequiredMixin, generic.ListView):
	model = Classe
