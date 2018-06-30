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

from pykol.lib.navigation import item, nav

nav.register(item(name="home",
	label="Tableau de bord",
	url="home",
	icon="bar-chart",
	))

nav.register(item(name="home",
	label="Mon profil",
	url="home",
	icon="bar-chart",
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
		),
		item(
			name="colles_planning",
			label="Planning",
		),
		item(
			name="colles_releve_heures",
			label="Relevés d'heures",
			icon="clone",
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
			icon="users",
		),
	)
)
nav.register(parametrage)

colloscopes = item(name="colloscope_home",
	label="Colloscopes",
	url="colloscope_home",
	icon="calendar",
	children=(
		item(name="creneau_list_direction",
			label="Créneaux",
			url="creneau_list_direction",
			icon="fort-awesome"),
		item(name="reservation_ponctuelle",
			label="Réservations ponctuelles",
			icon="calendar"),
		# TODO entrées pour les classes
	)
)
nav.register(colloscopes)

nav.register(item(name="classes",
	label="Classes",
	url="classe_list",
	icon="chalkboard-teacher",
	))

nav.register(item(name="logout",
	label="Déconnexion",
	url="logout",
	icon="power-off"))
