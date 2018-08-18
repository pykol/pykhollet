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
			nature_uai = int(ligne['nature_uai'])

			# On importe uniquement les lycées généraux
			if nature_uai < 300 or nature_uai >= 310:
				continue

			# Formatage de l'adresse
			if ligne['boite_postale_uai']:
				ligne['boite_postale_uai'] = "BP" + ligne['boite_postale_uai']
			adresse = norm("{adresse_uai}\n" \
					"{lieu_dit_uai}\n" \
					"{boite_postale_uai}\n" \
					"{code_postal_uai} {localite_acheminement_uai}".format(**ligne))

			denomination = norm("{denomination_principale} {patronyme_uai}".format(**ligne))

			appellation = norm(ligne['appellation_officielle']) or denomination

			etablissements.append({
				'model': 'pykol.etablissement',
				'pk': ligne['numero_uai'],
				'fields': {
					'appellation': appellation,
					'denomination': denomination,
					'adresse': adresse,
					'nature_uai': int(ligne['nature_uai']),
				}
			})

	print(json.dumps(etablissements, indent=4))

main()
