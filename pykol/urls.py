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
	path('', views.colles.colloscope_home, name='colloscope_home'),
	path('<slug:slug>/', views.colles.colloscope, name='colloscope'),
	path('<slug:slug>/trinomes', views.colles.trinomes, name='trinomes'),
	path('<slug:slug>/semaines', views.colles.semaines, name='semaines'),
]

direction_urlpatterns = [
	path('import_bee/', views.direction.import_bee, name='import_bee'),
]

annees_urlpatterns = [
	path('', views.direction.AnneeListView.as_view(), name='annee_list'),
	path('<int:pk>/', views.direction.AnneeDetailView.as_view(), name='annee_detail'),
	path('<int:pk>/supprimer', views.direction.annee_supprimer, name='annee_supprimer'),
]

urlpatterns = [
	path('', views.home, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
	path('colles/', include(colles_urlpatterns)),
	path('direction/', include(direction_urlpatterns)),
	path('annees/', include(annees_urlpatterns)),
	path('classes/<slug:slug>/', views.ClasseDetailView.as_view(), name='classe_detail'),
]
