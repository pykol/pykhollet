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

from django import forms
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.text import capfirst
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from pykol.models.base import User, Professeur, Etudiant, JetonAcces
from pykol.models.base import Academie, Annee, Vacances, Etablissement
from pykol.models.base import Matiere, Classe, Enseignement, Service, Groupe

class PykolAdminSite(admin.AdminSite):
	site_header = 'Administration de pyKol'
	site_title = 'Administration de pyKol'
admin_site = PykolAdminSite(name="pykol_admin")

def register(*models, **kwargs):
	kwargs['site'] = admin_site
	return admin.register(*models, **kwargs)

class PykolUserCreationForm(forms.ModelForm):
	password1 = forms.CharField(label=_("Password"),
			widget=forms.PasswordInput, required=False)
	password2 = forms.CharField(label=_("Password confirmation"),
		widget=forms.PasswordInput,
		help_text=_("Enter the same password as above, for verification."),
		required=False)
	class Meta:
		model = User
		fields = ('sexe', 'email')

@register(User)
class PykolUserAdmin(UserAdmin):
	add_form = PykolUserCreationForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('password1', 'password2', 'sexe', 'email'),
			}),)
	fieldsets = (
		(None, {'fields': ('password',)}),
		(_('Personal info'), {'fields': ('first_name', 'last_name', 'sexe', 'email')}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
		)

	ordering = ('email',)
	list_display = ('email', 'first_name', 'last_name', 'is_staff')
	search_fields = ('first_name', 'last_name', 'email')

class ProfesseurCreationForm(PykolUserCreationForm):
	email = forms.EmailField(required=True)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		UserModel = get_user_model()
		self.username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
		if self.fields['username'].label is None:
			self.fields['username'].label = capfirst(self.username_field.verbose_name)

	class Meta:
		model = Professeur
		fields = ('sexe', 'email', 'corps', 'etablissement')

	def save(self, commit=True):
		user = super().save(commit=False)
		user.set_unusable_password()
		if commit:
			user.save()
		return user


@register(Professeur)
class ProfesseurAdmin(PykolUserAdmin):
	add_form = ProfesseurCreationForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('last_name', 'first_name', 'sexe',
				'email', 'corps', 'etablissement'),
			}),)
	fieldsets = (
		(None, {'fields': ('password',)}),
		(_('Personal info'), {'fields': ('first_name', 'last_name',
			'sexe', 'email', 'corps', 'id_acad')}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
		)

class EtudiantCreationForm(PykolUserCreationForm):
	class Meta:
		model = Etudiant
		fields = ('sexe', 'email', 'ine', 'classe')

	def save(self, commit=True):
		user = super(EtudiantCreationForm, self).save(commit=False)
		user.set_unusable_password()
		if commit:
			user.save()
		return user


@register(Etudiant)
class EtudiantAdmin(PykolUserAdmin):
	add_form = EtudiantCreationForm
	add_fieldsets = ((None, {
			'classes': ('wide',),
			'fields': ('password1', 'password2', 'sexe',
				'email', 'ine', 'classe'),
			}),)
	fieldsets = (
		(None, {'fields': ('password',)}),
		(_('Personal info'), {'fields': ('first_name', 'last_name',
			'sexe', 'email', 'ine',)}),
		('Scolarité', {'fields': ('classe', 'origine',)}),
		(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
									   'groups', 'user_permissions')}),
		(_('Important dates'), {'fields': ('last_login', 'date_joined',
			'entree', 'sortie')}),
		)

admin_site.register(Etablissement)

class VacancesInline(admin.TabularInline):
	model = Vacances
@register(Annee)
class AnneeAdmin(admin.ModelAdmin):
	inlines = [VacancesInline,]

admin_site.register(Academie)

admin_site.register(Matiere)

class ServiceInline(admin.TabularInline):
	model = Service
	extra = 0
@register(Enseignement)
class EnseignementAdmin(admin.ModelAdmin):
	inlines = [ServiceInline,]
	list_display = ('__str__', 'classe',)
	list_filter = ('classe__annee', 'classe',)

class EnseignementInline(admin.TabularInline):
	model = Enseignement
	extra = 3
	show_change_link = True
	fk_name = 'classe'

class EtudiantInline(admin.TabularInline):
	model = Etudiant
	extra = 0
	show_change_link = True
	readonly_fields = ('__str__',)
	fields = ('__str__',)
	fk_name = 'classe'
	can_delete = False

	def has_add_permission(self, *args):
		return False

admin_site.register(Groupe)

@register(Classe)
class ClasseAdmin(admin.ModelAdmin):
	fieldsets = (
			(None, {
				'fields': (('nom', 'niveau', 'annee', 'mef'), 'slug', 'coordonnateur',),
				}),
			)
	inlines = [EnseignementInline, EtudiantInline]
	list_display = ('nom', 'annee')

admin_site.register(JetonAcces)
