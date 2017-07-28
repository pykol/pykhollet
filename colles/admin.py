# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from base.admin import admin_site
from .models import Semaine, Creneau, Colle, Roulement, RoulementLigne

class SemaineAdmin(admin.ModelAdmin):
	fields = ('classe', 'numero', 'debut', 'fin')
	list_display = ['__str__', 'classe']
	list_filter = ('classe',)
admin_site.register(Semaine, SemaineAdmin)

admin_site.register(Creneau)
admin_site.register(Colle)

class RoulementLigneInline(admin.TabularInline):
	model = RoulementLigne
	extra = 3

class RoulementAdmin(admin.ModelAdmin):
	inlines = [RoulementLigneInline,]
admin_site.register(Roulement, RoulementAdmin)
