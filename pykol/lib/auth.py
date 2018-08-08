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

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import user_passes_test

from pykol.models.base import Classe
from pykol.models.colles import ColloscopePermission, Colle

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

		# Permissions du colloscope
		if isinstance(obj, Classe):
			perms = ColloscopePermission.objects.filter(user=user_obj,
					classe=obj).values_list('droit__content_type__app_label',
							'droit__codename').order_by()
			return {"%s.%s" % (ct, name) for ct, name in perms}

		# Permission pour chaque colle
		if isinstance(obj, Colle):
			# TODO le responsable du colloscope aussi devrait avoir
			# cette permission
			if user_obj == obj.colleur:
				return {"pykol.change_colle"}

		return set()

def user_has_object_perm(user, model, perm, **kwargs):
	# TODO cache
	if model != Classe:
		return False

	classe = Classe.objects.get(**kwargs)
	# TODO requête pour la permission à partir de son nom ?
	return ColloscopePermission.objects.exists(user=user, classe=classe,
			droit=perm)

def object_permission_required(model, perm, **kwargs):
	return user_passes_test(
			lambda u: user_has_object_perm(u, model, perm, **kwargs))

user_est_professeur = user_passes_test(
	lambda user: user.professeur is not None)

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
	supprimer_perm = user.has_perm('pykol.change_colle', colle.classe)
	noter_perm = user == colle.colleur.user_ptr
	deplacer_perm = user.has_perm('pykol.change_colle', colle.classe)
	annuler_perm = user.has_perm('pykol.change_colle', colle.classe)

	return CollePermissions(
			supprimer=supprimer_perm,
			annuler=annuler_perm,
			deplacer=deplacer_perm,
			noter=noter_perm)
