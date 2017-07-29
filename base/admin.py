# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.admin import AdminSite
from .models import User, Professeur, Etudiant
from .models import Academie, Annee, Etablissement

class PykolAdminSite(AdminSite):
	site_header = 'Administration de pyKol'
	site_title = 'Administration de pyKol'
admin_site = PykolAdminSite(name="pykol_admin")


from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
class PykolUserCreateForm(UserCreationForm):
	class Meta:
		model = User
		fields = ('username', 'sexe', 'email',)
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

admin_site.register(User, PykolUserAdmin)
admin_site.register(Professeur, ProfesseurAdmin)
admin_site.register(Etudiant, EtudiantAdmin)


admin_site.register(Etablissement)
admin_site.register(Annee)


from import_export import resources
from import_export.admin import ImportExportModelAdmin

class AcademieResource(resources.ModelResource):
	class Meta:
		model = Academie
class AcademieAdmin(ImportExportModelAdmin):
	resource_class = AcademieResource
admin_site.register(Academie, AcademieAdmin)
