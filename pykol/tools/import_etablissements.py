#! env python3
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

"""
Import de la liste des établissements depuis un fichier CSV

https://www.data.gouv.fr/fr/datasets/adresse-et-geolocalisation-des-etablissements-denseignement-du-premier-et-second-degres-1/
"""

import sys
import csv
import json
import re

def norm(chaine):
	return re.sub('\n+', '\n', chaine.strip())

def main():
	etablissements = []

	with open(sys.argv[1], 'r') as etab_file:
		etab_csv = csv.DictReader(etab_file, delimiter=';')

		for idx, ligne in enumerate(etab_csv):
			nature_uai = int(ligne['Code nature'])

			# On importe uniquement les lycées généraux
			if nature_uai < 300 or nature_uai >= 310:
				continue

			# Formatage de l'adresse
			donnees_adresse = {}
			if ligne['Boite postale']:
				donnees_adresse['boite_postale'] = "BP" + ligne['Boite postale']
			else:
				donnees_adresse['boite_postale'] = ""

			donnees_adresse['adresse'] = ligne['Adresse']
			donnees_adresse['lieu_dit'] = ligne['Lieu dit']
			donnees_adresse['code_postal'] = ligne['Code postal']
			donnees_adresse['localite'] = ligne['Localite d\'acheminement']

			adresse = norm("{adresse}\n" \
					"{lieu_dit}\n" \
					"{boite_postale}\n" \
					"{code_postal} {localite}".format(**donnees_adresse))

			denomination = norm("{denomination_principale} {patronyme}".format(
				denomination_principale=ligne['Dénomination principale'],
				patronyme=ligne['Patronyme uai']))

			appellation = norm(ligne['Appellation officielle']) or denomination

			ville = norm(ligne['Commune'])

			etablissements.append({
				'model': 'pykol.etablissement',
				'pk': ligne['Code établissement'],
				'fields': {
					'appellation': appellation,
					'denomination': denomination,
					'adresse': adresse,
					'nature_uai': nature_uai,
					'ville': ville,
				}
			})

	print(json.dumps(etablissements, indent=4))

main()
