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

from django.urls import reverse

from pykol.lib.navigation import item, nav, MesClassesChildren

nav.register(item(name="home",
	label="Tableau de bord",
	url="home",
	icon="chart-bar",
	))

nav.register(item(name="home",
	label="Mon profil",
	url="mon_profil",
	icon="user",
	))

mes_colles = item(
	name="mes_colles",
	label="Mes colles",
	icon="question",
	children=(
		item(
			name="colles_a_noter",
			label="À noter",
			icon="edit",
			url="colles_a_noter",
		),
		item(
			name="colles_planning",
			label="Planning",
			icon="calendar-alt",
			url="colle_list",
		),
		item(
			name="colles_releve_heures",
			label="Relevés d'heures",
			icon="clone",
			url="releve_list",
		),
	)
)

nav.register(mes_colles)

parametrage = item(
	name="parametrage",
	label="Paramétrage",
	icon="wrench",
	permissions=("pykol.direction",),
	children=(
		item(name="annee_list",
			label="Années scolaires",
			url="annee_list",
			icon="calendar-plus",
			permissions=("pykol.direction",)
		),

		item(name="import_bee",
			label="Import SIECLE/STS",
			url="import_bee",
			icon="download",
		),

		item(name="utilisateurs",
			label="Utilisateurs",
			url='direction_list_user',
			icon="users",
		),
	)
)
nav.register(parametrage)

colloscopes = item(name="colloscope_home",
	label="Colloscopes",
	icon="calendar",
	permissions=('pykol.direction',),
	children=(
		item(name="creneau_list_direction",
			label="Créneaux",
			url="creneau_list_direction",
			icon="stream"),
		item(name="reservation_ponctuelle",
			label="Réservations ponctuelles",
			icon="calendar"),
		# TODO entrées pour les classes
	)
)
nav.register(colloscopes)

classes = item(name="classes",
	label="Classes",
	icon="chalkboard-teacher",
	)
classes.children = MesClassesChildren()
nav.register(classes)

gestion = item(name="gestion",
	label="Gestion",
	icon="paperclip",
	permissions=('pykol.direction',),
	children=(
		item(name="utilisateurs",
			label="Utilisateurs",
			url='direction_list_user',
			icon="users",
		),
		item(name="releve_list",
			label="Relevés",
			url='releve_list',
			icon="tasks",
		),
	)
)
nav.register(gestion)

nav.register(item(name="logout",
	label="Déconnexion",
	url="logout",
	icon="power-off"))
