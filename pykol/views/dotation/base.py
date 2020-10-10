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

from datetime import timedelta

from django.db.models import Sum
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

from pykol.models.base import Classe

class BaseView(TemplateView):
	template_name = 'pykol/dotation/base.html'

class ClasseDetailView(DetailView):
	template_name = 'pykol/dotation/classe_detail.html'

	def get_queryset(self):
		return Classe.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)

		classe = self.object

		# Calcul des dotations théoriques pour les classes et des heures
		# prévues aux colloscopes.
		colles_ens = classe.collesenseignement_set.all()
		dotations = []
		total_heures = timedelta()
		total_heures_colloscopes = timedelta()
	
		for ligne in colles_ens:
			heures = ligne.dotation()
			heures_colloscope = ligne.colle_set.aggregate(Sum('duree'))['duree__sum'] \
					or timedelta()
			dotations.append({
				'matiere': ligne,
				'heures': heures,
				'heures_colloscope': heures_colloscope,
				'heures_restantes': ligne.compte_colles.solde(classe.annee)['duree'],
				})
			total_heures += heures
			total_heures_colloscopes += heures_colloscope

		context['heures_theoriques'] = total_heures
		context['heures_utilisees'] = total_heures_colloscopes
		context['heures_restantes'] = classe.compte_colles.solde(classe.annee)['duree']
		context['dotations'] = dotations

		return context

	def post(self):
		pass

class CompteDetailView(TemplateView):
	pass

class EnseignementDetailView(TemplateView):
	pass

class AjoutHeuresMatiereView(FormView):
	pass

class ParametresMatieresView(FormView):
	pass
