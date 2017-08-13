# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from base.admin import admin_site
from .models import Semaine, Creneau, Trinome, Roulement, RoulementLigne, Colle

class SemaineAdmin(admin.ModelAdmin):
	fields = ('classe', 'numero', 'debut', 'fin')
	list_display = ['__str__', 'classe']
	list_filter = ('classe',)
admin_site.register(Semaine, SemaineAdmin)

admin_site.register(Creneau)

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

class RoulementAdmin(admin.ModelAdmin):
	inlines = [RoulementLigneInline,]
admin_site.register(Roulement, RoulementAdmin)

admin_site.register(Colle)
