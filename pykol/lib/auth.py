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

from collections import namedtuple

from django.db.models import F, Q
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import user_passes_test

from pykol.models.base import Classe, Enseignement
from pykol.models.colles import ColloscopePermission, Colle, \
		ColleNote, Creneau, Trinome, PeriodeNotation

def perm_colloscope_qs(professeur, classe, matiere=None,
		matiere_seulement=True):
	"""
	Requête de base pour chercher toutes les permissions sur le
	colloscope de la classe pour ce professeur.
	"""
	qs = ColloscopePermission.objects.filter(
			user=professeur,
			classe=classe,
			droit__content_type__app_label='pykol',
			)
	if matiere_seulement:
		qs = qs.filter(
			Q(matiere_seulement=False) |
			Q(
				matiere_seulement=True,
				classe__enseignements__professeurs=F('user'),
				classe__enseignements__matiere=matiere
			)
		)

	return qs

def perm_colloscope(professeur, classe, matiere=None):
	"""
	Fonction qui renvoie True si et seulement si le professeur possède
	la permission pykol.change_colloscope dans la classe donnée, pour la
	matière donnée.
	"""
	return perm_colloscope_qs(professeur, classe, matiere).filter(
			droit__codename='change_colloscope').exists()

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

		# Permissions relatives au colloscope sur une classe complète
		if isinstance(obj, Classe):
			perms_qs = perm_colloscope_qs(professeur=user_obj,
					matiere_seulement=False,
					classe=obj).values_list('droit__content_type__app_label',
							'droit__codename')
			perms = {"%s.%s" % (ct, name) for ct, name in perms_qs}

			# La direction possède le droit de voir le colloscope
			if user_obj.has_perm('pykol.direction'):
				perms.add('pykol.view_colloscope')

			# Les professeurs et colleurs de la classe peuvent voir le
			# colloscope sans permission explicite.
			if professeur_dans(user_obj, obj):
				perms.update(('pykol.view_colloscope',
					'pykol.view_resultats'))

			# La gestion du colloscope donne le droit de le voir et
			# éventuellement d'ajouter des créneaux.
			perms_qs = perms_qs.filter(droit__codename='change_colloscope')
			if perms_qs:
				perms.update(('pykol.view_colloscope',
					'pykol.add_colle'))
				if perms_qs.filter(matiere_seulement=False):
					perms.update(('pykol.add_creneau',
						'pykol.change_trinome', 'pykol.change_semaine',
						'pykol.change_creneau'))

			return perms

		if isinstance(obj, Enseignement):
			perms = set()

			# Le professeur de la classe peut voir et modifier les
			# périodes de notation des colles dans ses propres matières.
			try:
				if user_obj.professeur in obj.classe.profs_de(obj.matiere):
					perms.update(('pykol.add_periodenotation',
						'pykol.change_periodenotation',
						'pykol.delete_periodenotation'))
			except:
				pass

			return perms

		# Permissions pour chaque colle
		if isinstance(obj, Colle):
			perms = set()
			classe = obj.classe
			matiere_colle = obj.matiere

			# On regarde si l'utilisateur a les droits de modification
			# du colloscope de la classe
			if perm_colloscope(professeur=user_obj,
					matiere=matiere_colle, classe=classe):
				perms.update(('pykol.add_colle', 'pykol.change_colle',
					'pykol.delete_colle', 'pykol.add_colledetails',
					'pykol.view_colle'))

			# Le colleur peut apporter des modifications à ses colles et
			# les noter.
			try:
				if user_obj == obj.colleur.user_ptr:
					perms.update(('pykol.change_colle',
						'pykol.view_colle', 'pykol.add_collenote',
						'pykol.add_colledetails'))
			except:
				pass

			# Le professeur de la classe peut voir et modifier les
			# colles de ses propres matières.
			try:
				if user_obj.professeur in obj.classe.profs_de(obj.matiere):
					perms.update(('pykol.change_colle',
						'pykol.view_colle'))
			except:
				pass

			return perms

		# Permissions sur la notation des colles
		if isinstance(obj, ColleNote):
			perms = set()
			# Seul le colleur a le droit de noter ses propres colles
			if user_obj == obj.colleur.user_ptr:
				perms.add('pykol.add_collenote')

			return perms

		# Permissions sur les créneaux de colles
		if isinstance(obj, Creneau):
			perms = set()
			# Le professeur en charge du colloscope peut ajouter un
			# créneau de colle, avec éventuellement une restriction si
			# la permission pykol.change_colloscope est limitée à sa
			# propre matière.
			# La direction peut toucher au colloscope.
			if perm_colloscope(professeur=user_obj, matiere=obj.matiere,
					classe=obj.classe) or \
						user_obj.has_perm('pykol.direction'):
				perms.update(('pykol.add_creneau',
					'pykol.delete_creneau',
					'pykol.change_creneau'))

			return perms

		# Permissions sur les groupes de colles
		if isinstance(obj, Trinome):
			perms = set()
			if perm_colloscope(professeur=user_obj, matiere=None,
					classe=obj.classe):
				perms.update(('pykol.change_trinome',
					'pykol.delete_trinome', 'pykol.add_trinome'))
			return perms

		# Permissions sur les périodes de notation
		if isinstance(obj, PeriodeNotation):
			perms = set()
			if obj.enseignement.professeurs.filter(pk=user_obj.pk).exists():
				perms.update(('pykol.change_periodenotation',
					'pykol.delete_periodenotation',
					'pykol.add_periodenotation'))
			return perms

		return set()

user_est_professeur = user_passes_test(lambda user: hasattr(user, 'professeur'))

def professeur_dans(user, classe):
	"""
	Teste si un utilisateur est un professeur et s'il enseigne dans la
	classe.
	"""
	try:
		return classe in user.professeur.mes_classes()
	except:
		return False


# Résumé des permissions accordées à un utilisateur sur une colle donnée
CollePermissions = namedtuple('CollePermissions', (
	'supprimer', 'annuler', 'deplacer', 'noter',
	))
def colle_user_permissions(user, colle):
	supprimer_perm = user.has_perm('pykol.change_colle', colle)
	noter_perm = user == colle.colleur.user_ptr
	deplacer_perm = user.has_perm('pykol.change_colle', colle)
	annuler_perm = user.has_perm('pykol.change_colle', colle)

	return CollePermissions(
			supprimer=supprimer_perm,
			annuler=annuler_perm,
			deplacer=deplacer_perm,
			noter=noter_perm)
