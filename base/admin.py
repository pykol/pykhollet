# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext, gettext_lazy as _
from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.admin import UserAdmin

from .models import User, Professeur, Etudiant
from .models import Academie, Annee, Etablissement
from .models import Matiere, Classe, Enseignement, Service

class PykolAdminSite(admin.AdminSite):
	site_header = 'Administration de pyKol'
	site_title = 'Administration de pyKol'
admin_site = PykolAdminSite(name="pykol_admin")

def register(*models, **kwargs):
	kwargs['site'] = admin_site
	return admin.register(*models, **kwargs)

class PykolUserCreateForm(UserCreationForm):
	class Meta:
		model = User
		fields = ('username', 'sexe', 'email',)

@register(User)
class PykolUserAdmin(UserAdmin):
	add_form = PykolUserCreateForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('username', 'password1', 'password2', 'sexe', 'email'),
			}),)
	fieldsets = (
		(None, {'fields': ('username', 'password')}),
		(_('Personal info'), {'fields': ('first_name', 'last_name', 'sexe', 'email')}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
		)

class ProfesseurCreateForm(PykolUserCreateForm):
	class Meta:
		model = Professeur
		fields = ('username', 'sexe', 'email', 'corps', 'etablissement')

@register(Professeur)
class ProfesseurAdmin(PykolUserAdmin):
	add_form = ProfesseurCreateForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('username', 'password1', 'password2', 'sexe',
				'email', 'corps', 'etablissement'),
			}),)
	fieldsets = (
		(None, {'fields': ('username', 'password')}),
		(_('Personal info'), {'fields': ('first_name', 'last_name',
			'sexe', 'email', 'corps')}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
		)

class EtudiantCreateForm(PykolUserCreateForm):
	class Meta:
		model = Etudiant
		fields = ('username', 'sexe', 'email', 'ine', 'classe')

@register(Etudiant)
class EtudiantAdmin(PykolUserAdmin):
	add_form = EtudiantCreateForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('username', 'password1', 'password2', 'sexe',
				'email', 'ine', 'classe'),
			}),)
	fieldsets = (
		(None, {'fields': ('username', 'password')}),
		(_('Personal info'), {'fields': ('first_name', 'last_name',
			'sexe', 'email', 'ine',)}),
		('Scolarité', {'fields': ('classe', 'origine', 'options')}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined',
			'entree', 'sortie')}),
		)

admin_site.register(Etablissement)
admin_site.register(Annee)


from import_export import resources
from import_export.admin import ImportExportModelAdmin

class AcademieResource(resources.ModelResource):
	class Meta:
		model = Academie

@register(Academie)
class AcademieAdmin(ImportExportModelAdmin):
	resource_class = AcademieResource

admin_site.register(Matiere)

class ServiceInline(admin.TabularInline):
	model = Service
	extra = 0
@register(Enseignement)
class EnseignementAdmin(admin.ModelAdmin):
	inlines = [ServiceInline,]

class EnseignementInline(admin.TabularInline):
	model = Enseignement
	extra = 3
	show_change_link = True

class EtudiantInline(admin.TabularInline):
	model = Etudiant
	extra = 0
	show_change_link = True
	readonly_fields = ('__str__',)
	fields = ('__str__', 'entree', 'sortie',)
	fk_name = 'classe'
	can_delete = False

	def has_add_permission(self, request):
		return False

@register(Classe)
class ClasseAdmin(admin.ModelAdmin):
	fieldsets = (
			(None, {
				'fields': (('nom', 'niveau', 'annee'), 'slug', 'coordonnateur',),
				}),
			)
	inlines = [EnseignementInline, EtudiantInline]
