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

from django.conf.urls import url
from django.urls import path, include

from . import views

colles_urlpatterns = [
	path('', views.colles.colle_list, name='colle_list'),
	path('a_noter/', views.colles.colle_a_noter_list, name="colles_a_noter"),
	path('<int:pk>/', views.colles.colle_detail, name='colle_detail'),
	path('<int:pk>/noter', views.colles.colle_declarer, name='colle_declarer'),
	path('<slug:slug>/', views.colles.colloscope, name='colloscope'),
	path('<slug:slug>/roulement/creer', views.colloscope.roulement_creer, name='roulement_creer'),
]

colloscopes_urlpatterns = [
	path('', views.colles.colloscope_home, name='colloscope_home'),
	path('<slug:slug>/trinomes', views.colles.trinomes, name='colloscope_trinomes'),
	path('<slug:slug>/semaines', views.colles.semaines, name='colloscope_semaines'),
	path('<slug:slug>/creneaux', views.colles.creneaux, name='colloscope_creneaux'),
	path('roulement/<int:pk>', views.colloscope.roulement_editer, name='roulement_editer'),
	path('roulement/<int:pk>/application_creer', views.colloscope.roulement_application_creer, name='roulement_application_creer'),
	path('roulement/application/<int:pk>/', views.colloscope.roulement_application_editer, name='roulement_application_editer'),
	path('roulement/application/<int:pk>/generer', views.colloscope.roulement_generer_colles, name='roulement_generer_colles'),
]

direction_urlpatterns = [
	path('import_bee/', views.direction.import_bee, name='import_bee'),
	path('creneaux/', views.colles.creneau_list_direction, name='creneau_list_direction'),
]

annees_urlpatterns = [
	path('', views.direction.AnneeListView.as_view(), name='annee_list'),
	path('<int:pk>/', views.direction.annee_detail, name='annee_detail'),
	path('<int:pk>/supprimer', views.direction.annee_supprimer, name='annee_supprimer'),
]

classes_urlpatterns = [
	path('', views.ClasseListView.as_view(), name="classe_list"),
	path('<slug:slug>/', views.ClasseDetailView.as_view(), name='classe_detail'),
	path('<slug:slug>/resultats', views.colles.classe_resultats, name='classe_colle_resultats'),
]

etudiants_urlpatterns = [
    path('<int:pk>/', views.EtudiantDetailView.as_view(), name='etudiant'),
    path('<int:pk>/resultats', views.colles.resultats.etudiant_resultats, name='classe_etudiant_resultats'),
]

accounts_urlpatterns = [
	path('', views.direction.DirectionListUser.as_view(), name='direction_list_user'),
	path('profile/', views.mon_profil, name='mon_profil'),
	path('create/', views.direction.direction_create_user, name='direction_create_user'),
	path('edit/<int:pk>/', views.direction.direction_edit_user, name='direction_edit_user'),
	path('delete/<int:pk>/', views.direction.direction_delete_user, name='direction_delete_user'),
	path('', include('django.contrib.auth.urls')),
]

releves_urlpatterns = [
	path('', views.direction.ReleveListView.as_view(), name='releve_list'),
	path('creer/', views.direction.releve_creer, name='releve_creer'),
	path('<int:pk>/', views.direction.ReleveDetailView.as_view(), name='releve_detail'),
	path('<int:pk>/payer/', views.direction.releve_payer, name='releve_payer'),
]

urlpatterns = [
	path('', views.home, name='home'),
	path('accounts/', include(accounts_urlpatterns)),
	path('colles/', include(colles_urlpatterns)),
	path('colloscopes/', include(colloscopes_urlpatterns)),
	path('direction/', include(direction_urlpatterns)),
	path('annees/', include(annees_urlpatterns)),
	path('classes/', include(classes_urlpatterns)),
	path('etudiant/', include(etudiants_urlpatterns)),
	path('releves/', include(releves_urlpatterns)),
]
