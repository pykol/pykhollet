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

from django.contrib import admin

from pykol.admin.base import register, admin_site
from pykol.models.colles import Semaine, Creneau, Trinome, Roulement, \
		RoulementLigne, Colle, ColleDetails, CollesEnseignement, \
		ColleNote

@register(Semaine)
class SemaineAdmin(admin.ModelAdmin):
	fields = ('classe', 'numero', 'debut', 'fin')
	list_display = ['__str__', 'classe']
	list_filter = ('classe',)

@register(Creneau)
class CreneauAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'classe', 'matiere', 'colleur']
	list_filter = ('classe', 'colleur')

class TrinomeInline(admin.TabularInline):
	model = Trinome
	extra = 3
	fk_name = 'classe'
	fields = ('nom',)
	show_change_link = True

from pykol.admin.base import ClasseAdmin
ClasseAdmin.inlines.append(TrinomeInline)

class RoulementLigneInline(admin.TabularInline):
	model = RoulementLigne
	extra = 3

@register(Roulement)
class RoulementAdmin(admin.ModelAdmin):
	inlines = [RoulementLigneInline,]

class ColleDetailsInline(admin.TabularInline):
	model = ColleDetails
	extra = 0

class ColleNoteInline(admin.TabularInline):
	model = ColleNote
	extra = 0

@register(Colle)
class ColleAdmin(admin.ModelAdmin):
	inlines = [ColleDetailsInline, ColleNoteInline]

@register(CollesEnseignement)
class CollesEnseignementAdmin(admin.ModelAdmin):
	list_display = ['__str__', ]

@register(ColleNote)
class ColleNoteAdmin(admin.ModelAdmin):
	list_display = ['id', 'heure_colle', 'matiere', 'eleve', 'note']
	list_filter = ['eleve__classe', 'colle__enseignement__matiere']
	search_fields = ['eleve__first_name', 'eleve__last_name']

	def matiere(self, collenote):
		return collenote.colle.enseignement.matiere

	def heure_colle(self, collenote):
		return collenote.colle.details.horaire
