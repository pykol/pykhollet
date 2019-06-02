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

from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin, TreeRelatedFieldListFilter

from pykol.admin.base import register, admin_site

from pykol.models.base import Annee
from pykol.models.comptabilite import Compte, Mouvement, \
		MouvementLigne, Lettrage

@register(Compte)
class CompteAdmin(DraggableMPTTAdmin):
	list_display = ('tree_actions', 'indented_title', 'admin_solde')
	autocomplete_fields = ('gestionnaires',)

	def admin_solde(self, obj):
		duree = obj.solde(Annee.objects.get_actuelle())['duree'] or \
				timedelta()
		return "{:.2f}h".format(duree.total_seconds() / 3600)
	admin_solde.short_description = "Solde d'heures"

class MouvementLigneInline(admin.TabularInline):
	model = MouvementLigne
	extra = 0

@register(Mouvement)
class MouvementAdmin(admin.ModelAdmin):
	autocomplete_fields = ('colle',)
	inlines = (MouvementLigneInline,)

@register(MouvementLigne)
class MouvementLigneAdmin(admin.ModelAdmin):
	list_display = ('pk', 'compte', 'duree', 'duree_interrogation')
	list_filter = (('compte', TreeRelatedFieldListFilter),)

@register(Lettrage)
class LettrageAdmin(admin.ModelAdmin):
	inlines= (MouvementLigneInline,)
