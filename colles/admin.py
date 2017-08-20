# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from base.admin import register, admin_site
from .models import Semaine, Creneau, Trinome, Roulement, \
		RoulementLigne, Colle, ColleDetails

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
	fk_name = 'dans_classe'
	fields = ('nom',)
	show_change_link = True
from base.admin import ClasseAdmin
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

@register(Colle)
class ColleAdmin(admin.ModelAdmin):
	inlines = [ColleDetailsInline,]
