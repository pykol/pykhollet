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

from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.shortcuts import get_object_or_404

from pykol.models.base import Enseignement, Professeur
from pykol.models.colles import Colle
from pykol.forms.colloscope import CalendrierColleurFormset

class CalendrierMatiereView(DetailView):
	"""
	Accès au calendrier de tous les colleurs dans une matière.
	"""
	model = Enseignement
	template_name = 'pykol/colloscope/calendrier/matiere.html'

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)

		context['colleur_list'] = Professeur.objects.filter(
			colledetails__colle__colles_ens__enseignements=self.get_object()
			).distinct().order_by('last_name', 'first_name')

		return context

class CalendrierMatiereColleurView(FormMixin, DetailView):
	"""
	Accès au calendrier d'un colleur dans une matière.
	"""
	model = Professeur
	template_name = 'pykol/colloscope/calendrier/colleur.html'
	pk_url_kwarg = 'colleur_pk'
	form_class = CalendrierColleurFormset

	def get_form_kwargs(self):
		form_kwargs = super().get_form_kwargs()
		form_kwargs['colleur'] = self.object
		form_kwargs['enseignement'] = self.get_enseignement()
		return form_kwargs

	def get_initial(self):
		initial = []
		for colle in Colle.objects.filter(
				colledetails__actif=True,
				colledetails__colleur=self.object,
				enseignement=self.get_enseignement()):
			initial.append({
				'colle': colle,
				'debut': colle.details.horaire,
				'duree_etudiant': colle.duree_etudiant,
			})
		return initial

	def get_enseignement(self):
		return get_object_or_404(Enseignement, pk=self.kwargs['matiere_pk'])

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['matiere'] = get_object_or_404(Enseignement, pk=self.kwargs['matiere_pk'])
		return context
