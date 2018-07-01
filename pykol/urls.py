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
	path('<slug:slug>/', views.colles.colloscope, name='colloscope'),
	path('<slug:slug>/trinomes', views.colles.trinomes, name='colloscope_trinomes'),
	path('<slug:slug>/semaines', views.colles.semaines, name='colloscope_semaines'),
	path('<slug:slug>/creneaux', views.colles.creneaux, name='colloscope_creneaux'),
]

direction_urlpatterns = [
	path('import_bee/', views.direction.import_bee, name='import_bee'),
	path('creneaux/', views.colles.creneau_list_direction, name='creneau_list_direction'),
]

annees_urlpatterns = [
	path('', views.direction.AnneeListView.as_view(), name='annee_list'),
	path('<int:pk>/', views.direction.AnneeDetailView.as_view(), name='annee_detail'),
	path('<int:pk>/supprimer', views.direction.annee_supprimer, name='annee_supprimer'),
]

classes_urlpatterns = [
	path('', views.ClasseListView.as_view(), name="classe_list"),
	path('<slug:slug>/', views.ClasseDetailView.as_view(), name='classe_detail'),
]

accounts_urlpatterns = [
	path('', views.DirectionListUser.as_view(), name='direction_list_user'),
	path('profile/', views.mon_profil, name='mon_profil'),
	path('create/', views.direction_create_user, name='direction_create_user'),
	path('edit/<int:pk>/', views.direction_edit_user, name='direction_edit_user'),
	path('delete/<int:pk>/', views.direction_delete_user, name='direction_delete_user'),
	path('', include('django.contrib.auth.urls')),
]

urlpatterns = [
	path('', views.home, name='home'),
	path('accounts/', include(accounts_urlpatterns)),
	path('colles/', include(colles_urlpatterns)),
	path('colloscopes/', views.colles.colloscope_home, name='colloscope_home'),
	path('direction/', include(direction_urlpatterns)),
	path('annees/', include(annees_urlpatterns)),
	path('classes/', include(classes_urlpatterns)),
	path('etudiant/<int:pk>/', views.EtudiantDetailView.as_view(), name='etudiant'),
]
