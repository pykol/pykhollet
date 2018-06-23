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

"""Import de données depuis la Base Élèves (application SIECLE)

Ce module fournit des fonctions pour importer les données exportées au
format XML depuis l'application SIECLE afin de peupler la base de
données de pyKol avec les listes des étudiants, des classes et des
options choisies par les étudiants.
"""

import xml.etree.ElementTree as ET
import datetime
import re

from django.utils.text import slugify

from pykol.models.base import Etudiant, Annee, Classe, Etablissement, \
		Groupe, Matiere, Enseignement

class CodeMEF:
	"""Gestion d'un code de Module Élémentaire de Formation

	Chaque Module Élémentaire de Formation (MEF) possède un code sur
	11 caractères qui l'identifie au niveau national. Le code est
	découpé en plusieurs parties pour lesquelles cette classe fournit
	des accès rapides.
	"""
	def __init__(self, code):
		# XXX faut-il vérifier la validité du code ? Comment ? Je ne
		# trouve de la documentation nulle part.
		self.code = code

	def dispositif(self):
		return int(self.code[0:3])

	def est_primaire(self):
		return 100 <= self.dispositif() < 200

	def est_secondaire(self):
		return 200 <= self.dispositif() < 300

	def est_superieur(self):
		return 300 <= self.dispositif()

	def categorie(self):
		return int(self.code[3])

	def domaine(self):
		return int(self.code[3:5])

	def groupe(self):
		return int(self.code[3:6])

	def numero_ordre(self):
		return int(self.code[6:8])

	def duree(self):
		return int(self.code[8])
	
	def annee(self):
		return int(self.code[9])

	def type_mef(self):
		return int(self.code[10])


def parse_date_francaise(date):
	mo = re.fullmatch(r'(?P<jour>\d+)/(?P<mois>\d+)/(?P<annee>\d+)',
			date)
	if not mo:
		print("date curieuse {}".format(date))
		return None
	return datetime.date(year=int(mo['annee']), month=int(mo['mois']),
			day=int(mo['jour']))

def import_etudiants(eleves_xml):
	"""Import de la liste des étudiants à partir du fichier XML

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons. Les étudiants déjà présents dans la base de données de
	pyKol seront mis à jour si les informations présentes dans le
	fichier XML diffèrent.

	Les étudiants sont identifiés par leur INE (provenant du RNIE).

	L'import des étudiants doit nécessairement être réalisé après
	l'import des structures, car la création d'un étudiant nécessite de
	le rattacher à une classe déjà existante dans la base de données.
	"""
	eleves_et = ET.parse(eleves_xml)

	# Préparation d'un dictionnaire des classes de l'année actuelle,
	# pour retrouver rapidement une classe à partir de son
	# code_structure.
	annee_actuelle = Annee.actuelle.all().first()
	divisions = dict([(str(c.code_structure), c) for c in
		Classe.objects.filter(annee=annee_actuelle)])

	# On construit ensuite le dictionnaire qui à chaque numéro d'élève
	# associe la classe dans laquelle l'étudiant est inscrit.
	classe_etudiant = {}
	for struct_eleve in eleves_et.getroot().findall('DONNEES/STRUCTURES/STRUCTURES_ELEVE'):
		code_structure = struct_eleve.find('STRUCTURE/CODE_STRUCTURE').text
		num_eleve = struct_eleve.attrib['ELENOET']
		if code_structure in divisions:
			classe_etudiant[num_eleve] = divisions[code_structure]

	# Enfin on peut créer ou mettre à jour les élèves dans la base de
	# données. Le dictionnaire classe_etudiant permet de mettre la main
	# sur la classe où affecter l'étudiant.
	for eleve in eleves_et.getroot().findall('DONNEES/ELEVES/ELEVE'):
		# On regarde si on connait la scolarité de l'an dernier
		origine = None
		#if eleve.find('SCOLARITE_AN_DERNIER'):
		#	uai_origine = eleve.find('SCOLARITE_AN_DERNIER/CODE_RNE').text
		#	# origine = Etablissement.objects.get(numero_uai=uai_origine)

		num_eleve = eleve.attrib['ELENOET']
		if not num_eleve in classe_etudiant:
			continue

		date_entree = parse_date_francaise(eleve.find('DATE_ENTREE').text)

		date_sortie = None
		date_sortie_et = eleve.find('DATE_SORTIE')
		if date_sortie_et:
			date_sortie = parse_date_francaise(date_sortie_et.text)

		email_et = eleve.find('MEL')
		if email_et:
			email = eleve.find('MEL').text
		else:
			email = 'nobody@nowhere.invalid'

		etudiant_data = {
			'classe': classe_etudiant[num_eleve],
			'entree': date_entree,
			'sortie': date_sortie,
			'origine': origine,
			'sexe': int(eleve.find('CODE_SEXE').text),
			'email': email,
			'first_name': eleve.find('PRENOM').text,
			'last_name': eleve.find('NOM_DE_FAMILLE').text,
			'username': eleve.attrib['ELEVE_ID'], # FIXME
			}
		etudiant_db, _ = Etudiant.objects.update_or_create(
				ine=eleve.find('INE_RNIE').text,
				defaults=etudiant_data)

		# TODO enregistrer les options suivies par chaque étudiant

	# Une fois que tous les étudiants ont été importés, on met à jour
	# les compositions des classes
	for division in divisions.values():
		division.update_etudiants()

def import_divisions(structures_xml):
	"""Import des divisions (classes) à partir du fichier Structures.xml

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons. Les divisions déjà présentes dans la base de données de
	pyKol seront mises à jour si les informations données dans le
	fichier XML diffèrent.

	Cette fonction écrit les modifications dans la base de données, en
	mettant à jour la table Classe.
	"""
	structures_et = ET.parse(structures_xml)

	# Création (ou mise à jour) des classes
	liste_classes = []
	annee_actuelle = Annee.actuelle.all().first()
	for division in structures_et.getroot().findall('DONNEES/DIVISIONS/DIVISION'):
		# On ne garde que les classes de l'enseignement supérieur
		if not any([CodeMEF(x.text).est_superieur() for x in 
			division.findall('./MEFS_APPARTENANCE/MEF_APPARTENANCE/CODE_MEF')]):
			continue

		# Le code_structure est l'identifiant unique de la classe dans
		# la base élèves.
		code_structure = division.attrib['CODE_STRUCTURE']
		liste_classes.append(code_structure)

		if 1 == max([CodeMEF(x.text).est_superieur() for x in 
			division.findall('./MEFS_APPARTENANCE/MEF_APPARTENANCE/CODE_MEF')]):
			classe_niveau = Classe.NIVEAU_PREMIERE_ANNEE
		else:
			classe_niveau = Classe.NIVEAU_DEUXIEME_ANNEE

		classe_data = {
			'code_structure': code_structure,
			'code_mef': division.find('MEFS_APPARTENANCE/MEF_APPARTENANCE/CODE_MEF').text,
			'slug': slugify("{annee}-{code}".format(annee=annee_actuelle, code=code_structure)),
			'nom': division.find('LIBELLE_LONG').text,
			'niveau': classe_niveau,
			'annee': annee_actuelle,
			'mode': Groupe.MODE_AUTOMATIQUE,
			}
		Classe.objects.update_or_create(code_structure=code_structure,
			defaults=classe_data)

def import_nomenclatures(nomenclatures_xml):
	"""Import des nomenclatures des classes à partir du fichier
	Nomenclatures.xml

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons. Elle renseigne dans la base de données les modules
	élémentaires de formation et les matières associées.
	"""
	nomenclatures_et = ET.parse(nomenclatures_xml)

	# On construit d'abord le dictionnaire des matières
	# TODO regrouper les LV dans une matière parent
	matieres = {}
	for matiere in nomenclatures_et.getroot().findall('DONNEES/MATIERES/MATIERE'):
		code_matiere = matiere.attrib['CODE_MATIERE']
		matieres[code_matiere] = {
				'code_nomenclature': code_matiere,
				'nom': matiere.find('LIBELLE_EDITION').text,
				'virtuelle': False,
				}

	# On construit le dictionnaire qui à chaque code MEF associe la
	# liste des classes relevant de ce code.
	annee_actuelle = Annee.actuelle.all().first()
	classe_par_mef = {}
	for classe in Classe.objects.filter(annee=annee_actuelle):
		if not classe.code_mef in classe_par_mef:
			classe_par_mef[classe.code_mef] = []

		classe_par_mef[classe.code_mef].append(classe)

	# On parcourt ensuite la liste des programmes et on attache chaque
	# matière aux classe possédant le code MEF indiqué pour la matière.
	for programme in nomenclatures_et.getroot().findall('DONNEES/PROGRAMMES/PROGRAMME'):
		code_mef = programme.find('CODE_MEF').text
		if not code_mef in classe_par_mef:
			continue

		# On crée ou on met à jour la matière en base de données
		code_matiere = programme.find('CODE_MATIERE').text

		matiere, _ = Matiere.objects.update_or_create(
				code_nomenclature=code_matiere,
				defaults=matieres[code_matiere])

		est_option = (programme.find('CODE_MODALITE_ELECT').text in ('O', 'F'))
		est_specialite = (programme.find('CODE_MODALITE_ELECT').text == 'O')

		for classe in classe_par_mef[code_mef]:
			enseignement, _ = Enseignement.objects.update_or_create(matiere=matiere,
					groupe=classe, defaults={
						'option': est_option,
						'specialite': est_specialite,
						})
			# Django ne crée pas de doublon en cas d'un nouvel ajout
			classe.enseignements.add(enseignement)
