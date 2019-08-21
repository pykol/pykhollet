# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018-2019 Florian Hatat
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

from collections import namedtuple, OrderedDict

from django.views.generic import DetailView, ListView, FormView
from django.views.generic.detail import SingleObjectMixin, \
		SingleObjectTemplateResponseMixin
from django.contrib.auth.mixins import LoginRequiredMixin, \
		PermissionRequiredMixin
from django.db.models import IntegerField, Func
from django.urls import reverse

from pykol.models.base import Classe, Service
from pykol.models.colles import Trinome
from pykol.forms.classe import ServiceFormset

class MaybeCast(Func):
	"""
	Fonction SQL qui convertit le début d'une chaine en entier. S'il n'y
	a pas de chiffres au début, renvoie None.
	"""
	function = "CAST"
	template = '%(function)s(%(expressions)s AS %(db_type)s)'

	def __init__(self, expression):
		super().__init__(expression, output_field=IntegerField(blank=True, null=True))

	def as_sql(self, compiler, connection, **extra_context):
		extra_context['db_type'] = self.output_field.cast_db_type(connection)
		return super().as_sql(compiler, connection, **extra_context)

	def as_sqlite(self, compiler, connection):
		return self.as_sql(compiler, connection, template='NULL')

	def as_postgresql(self, compiler, connection):
		return self.as_sql(compiler, connection,
				template="%(function)s(substring((%(expressions)s) FROM '^[0-9]+') AS %(db_type)s)")

	def as_mysql(self, compiler, connection):
		return self.as_sql(compiler, connection,
				template="%(function)s(REGEXP_SUBSTR((%(expression)s), '^[0-9]+') AS %(db_type)s)")

ClassePerm = namedtuple('ClassePerm',
		('view_resultats', 'change_colloscope', 'add_colle',
		'change_trinome', 'change_semaine', 'change_creneau',
		'change_roulement'))

class ClasseDetailView(LoginRequiredMixin, DetailView):
	"""
	Vue générale d'une classe
	"""
	model = Classe
	template_name = 'pykol/classe/detail.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		classe = self.get_object()

		etudiants = classe.etudiants.order_by('last_name',
				'first_name')
		context['etudiant_list'] = etudiants.exclude(sortie__isnull=False)
		context['etudiant_demissionnaire_list'] = etudiants.demissionnaire()

		classe_perm = ClassePerm._make([
			self.request.user.has_perm('pykol.{}'.format(f), classe)
			for f in ClassePerm._fields])
		context['classe_perm'] = classe_perm
		context['gestion_colloscope'] = any(classe_perm)

		periodes = OrderedDict()
		qs = classe.trinomes.annotate(
				nom_as_int=MaybeCast('nom')
				).order_by('nom_as_int', 'nom')
		for periode_id, periode_nom in reversed(Trinome.PERIODE_CHOICES):
			trinomes = qs.filter(periode=periode_id)
			if trinomes:
				periodes[periode_nom] = trinomes
		context['periodes'] = periodes

		# Accès au planning des colleurs pour les professeurs qui
		# peuvent programmer des colles dans la classe. On passe au
		# gabarit une liste des matières.
		# TODO filtrer selon la permission de créer des colles ?
		context['planning_colleurs'] = classe.enseignements.filter(
				service__professeur=self.request.user,
				collesenseignement__isnull=False).distinct().order_by(
					'matiere')

		return context

class ClasseListView(LoginRequiredMixin, ListView):
	model = Classe
	template_name = 'pykol/classe/list.html'

class ClasseServiceView(LoginRequiredMixin,
		PermissionRequiredMixin, SingleObjectMixin,
		SingleObjectTemplateResponseMixin,
		FormView):
	"""
	Vue qui permet de définir la liste des professeurs de la classe.
	"""
	model = Classe
	permission_required = ('pykol.change_service',)
	template_name = 'pykol/classe/service.html'
	form_class = ServiceFormset

	def get_success_url(self):
		return reverse('classe_service', args=(self.get_object().slug,))

	def dispatch(self, *args, **kwargs):
		self.object = self.get_object()
		return super().dispatch(*args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		classe = self.get_object()
		kwargs['form_kwargs'] = {'classe_qs': classe}
		kwargs['queryset'] = Service.objects.filter(enseignement__classe=classe
			).order_by('enseignement__matiere')
		return kwargs

	def form_valid(self, form):
		form.save()
		return super().form_valid(form)
