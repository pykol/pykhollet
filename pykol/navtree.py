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

from pykol.navigation import item, nav

nav.register(item(name="home",
	label="Tableau de bord",
	url="home",
	icon="bar-chart",
	))

parametrage = item(
		name="parametrage",
		label="Paramétrage",
		icon="wrench",
		permissions=("direction",))
nav.register(parametrage)

parametrage.children.append(item(name="import_bee",
	label="Import BEE",
	url="import_bee",
	icon="download",))

parametrage.children.append(item(name="annee_list",
	label="Années scolaires",
	url="annee_list",
	icon="download",
	permissions=("direction",)))

nav.register(item(name="colloscope_home",
	label="Colloscopes",
	url="colloscope_home",
	icon="calendar"))

nav.register(item(name="classes",
	label="Classes",
	icon="users",
	))

nav.register(item(name="logout",
	label="Déconnexion",
	url="logout",
	icon="power-off"))
