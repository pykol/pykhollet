# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from .models import User, Professeur, Etudiant
from .models import Academie, Annee, Etablissement

class PykolAdminSite(AdminSite):
	site_header = 'Administration de pyKol'
	site_title = 'Administration de pyKol'
admin_site = PykolAdminSite(name="pykol_admin")

class ProfesseurAdmin():
	pass
admin_site.register(User, UserAdmin)
admin_site.register(Professeur, UserAdmin)
admin_site.register(Etudiant, UserAdmin)

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
