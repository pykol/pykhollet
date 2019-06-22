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

from collections import namedtuple, OrderedDict

from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import IntegerField, Func

from pykol.models.base import Classe
from pykol.models.colles import Trinome

class MaybeCast(Func):
	"""
	Convertit le début d'une chaine en entier. S'il n'y a pas de
	chiffres au début, renvoie None.
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

class ClasseDetailView(LoginRequiredMixin, generic.DetailView):
	model = Classe

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		classe = self.get_object()

		etudiants = classe.etudiant_set.order_by('last_name',
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
		# TODO liste à créer
		context['planning_colleurs'] = []

		return context

class ClasseListView(LoginRequiredMixin, generic.ListView):
	model = Classe
