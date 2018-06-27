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

from pykol.models.base import User, Etudiant, Professeur, \
		Annee, Classe, Etablissement, \
		Groupe, Matiere, Enseignement, Service, \
		ModuleElementaireFormation

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

	def __str__(self):
		return str(self.code)


def parse_date_francaise(date):
	mo = re.fullmatch(r'(?P<jour>\d+)/(?P<mois>\d+)/(?P<annee>\d+)',
			date)
	if not mo:
		return None
	return datetime.date(year=int(mo['annee']), month=int(mo['mois']),
			day=int(mo['jour']))

def appartenance_mef_cpge(mef_appartenance_et):
	"""Fonction qui recherche si l'un des codes MEF est celui d'une CPGE

	Cette fonction prend en paramètre un fragment d'arbre etree qui
	correspond à un fragment XML de la forme :
        <MEFS_APPARTENANCE>
          <MEF_APPARTENANCE>
            <CODE_MEF>20112005110</CODE_MEF>
          </MEF_APPARTENANCE>
          <MEF_APPARTENANCE>
            <CODE_MEF>20112005112</CODE_MEF>
          </MEF_APPARTENANCE>
        </MEFS_APPARTENANCE>
	
	Elle accepte également la version STS-WEB :
		<MEF_APPARTENANCE CODE="20112005110"/>

	Elle renvoie une instance CodeMEF si l'une des balises CODE_MEF
	contient le code d'une CPGE, et None sinon.
	"""
	for code_mef in mef_appartenance_et.findall('MEF_APPARTENANCE'):
		if 'CODE' in code_mef.attrib: # Version STS-WEB
			m = CodeMEF(code_mef.attrib['CODE'])
		elif code_mef.find('CODE_MEF') is not None: # Version SIECLE
			m = CodeMEF(code_mef.find('CODE_MEF').text)
		else:
			continue

		if m.est_superieur():
			return m

	return None

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
		if date_sortie_et is not None and date_sortie_et.text:
			date_sortie = parse_date_francaise(date_sortie_et.text)

		email_et = eleve.find('MEL')
		if email_et is not None and email_et.text:
			email = email_et.text
		else:
			email = None

		etudiant_data = {
			'classe': classe_etudiant[num_eleve],
			'entree': date_entree,
			'sortie': date_sortie,
			'origine': origine,
			'sexe': int(eleve.find('CODE_SEXE').text),
			'email': email,
			'first_name': eleve.find('PRENOM').text.title(),
			'last_name': eleve.find('NOM_DE_FAMILLE').text.title(),
			}
		etudiant_db, _ = Etudiant.objects.update_or_create(
				ine=eleve.find('INE_RNIE').text,
				defaults=etudiant_data)

		# TODO enregistrer les options suivies par chaque étudiant

	# Une fois que tous les étudiants ont été importés, on met à jour
	# les compositions des classes
	for division in divisions.values():
		division.update_etudiants()

def creer_enseignements(classes, groupe, groupe_et, dict_profs):
	for service in groupe_et.findall('SERVICES/SERVICE'):
		code_matiere = service.attrib['CODE_MATIERE']
		try:
			matiere = Matiere.objects.get(code_matiere=code_matiere)
		except Matiere.DoesNotExist:
			# Il arrive que l'administration ne remplisse pas
			# correctement ses emplois du temps et ajoute des matières
			# qui ne sont pas dans le programme de la classe (c'est
			# souvent un cas d'homonymie sur des matières, qui existent
			# sous plusieurs codes selon les classes).
			continue

		# Pour l'instant, on ne préoccupe que des cours généraux, la
		# bonne solution serait de se contenter des programmes dans la
		# nomenclature.
		if service.attrib['CODE_MOD_COURS'] != 'CG':
			continue

		codes_enseignants = [x.attrib['ID'] for x in
				service.findall('ENSEIGNANTS/ENSEIGNANT')]
		# TODO et si la clé code_prof n'existe pas ?
		profs = [dict_profs[code_prof] for code_prof in codes_enseignants]

		enseignement, _ = Enseignement.objects.update_or_create(
				matiere=matiere,
				groupe=groupe,
				defaults={
					'matiere': matiere,
					'groupe': groupe,
					'option': False, # TODO
					'specialite': False, # TODO
					})

		for prof in profs:
			Service.objects.update_or_create(
					enseignement=enseignement,
					professeur=prof)

		# Ajouter l'enseignement aux classes
		for classe in classes:
			classe.enseignements.add(enseignement)

def import_divisions(divisions_et, dict_profs={}):
	"""Import des divisions (classes) à partir du fichier Structures.xml

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons. Les divisions déjà présentes dans la base de données de
	pyKol seront mises à jour si les informations données dans le
	fichier XML diffèrent.

	Cette fonction écrit les modifications dans la base de données, en
	mettant à jour la table Classe.
	"""
	# Création (ou mise à jour) des classes
	annee_actuelle = Annee.actuelle.all().first()
	for division in divisions_et.findall('DIVISION'):
		# On ne garde que les classes de l'enseignement supérieur
		code_mef = appartenance_mef_cpge(division.find('MEFS_APPARTENANCE'))
		if not code_mef:
			continue

		mef = ModuleElementaireFormation.objects.get(code_mef=code_mef)

		# Le code_structure est l'identifiant unique de la classe dans
		# la base élèves.
		if 'CODE_STRUCTURE' in division.attrib: # Version SIECLE
			code_structure = division.attrib['CODE_STRUCTURE']
		elif 'CODE' in division.attrib: # Version STS-WEB
			code_structure = division.attrib['CODE']
		else:
			continue # Curieux, pas de code pour la classe ?

		if code_mef.annee() == 1:
			classe_niveau = Classe.NIVEAU_PREMIERE_ANNEE
		else:
			classe_niveau = Classe.NIVEAU_DEUXIEME_ANNEE

		classe_data = {
			'code_structure': code_structure,
			'mef': mef,
			'slug': slugify("{annee}-{code}".format(annee=annee_actuelle, code=code_structure)),
			'nom': division.find('LIBELLE_LONG').text,
			'niveau': classe_niveau,
			'annee': annee_actuelle,
			'mode': Groupe.MODE_AUTOMATIQUE,
			}
		classe, _ = Classe.objects.update_or_create(
				code_structure=code_structure,
				annee=annee_actuelle,
				defaults=classe_data)

		creer_enseignements([classe], classe, division, dict_profs)

def import_groupes(groupes_et, dict_profs={}):
	annee_actuelle = Annee.actuelle.all().first()

	for groupe_et in groupes_et.findall('GROUPE'):
		# Récupération du code structure
		if 'CODE_STRUCTURE' in groupe_et.attrib: # Version SIECLE Structures.xml
			code_structure = groupe_et.attrib['CODE_STRUCTURE']
		elif 'CODE' in groupe_et.attrib: # Version STS-EMP
			code_structure = groupe_et.attrib['CODE']
		else:
			continue

		code_mef = appartenance_mef_cpge(groupe_et.find('MEFS_APPARTENANCE'))
		if not code_mef:
			continue

		# La première, c'est la version SIECLE, la deuxième c'est la
		# version STS-EMP. Ainsi, notre fonction se moque du fichier que
		# l'on a récupéré et marche dans tous les cas.
		codes_divisions = \
				{x.text for x in
					groupe_et.findall('DIVISIONS_APPARTENANCE/DIVISION_APPARTENANCE/CODE_STRUCTURE')} \
					| \
				{x.attrib['CODE']
					for x in groupe_et.findall('DIVISIONS_APPARTENANCE/DIVISION_APPARTENANCE')
					if 'CODE' in x.attrib}

		classes = Classe.objects.filter(
				code_structure__in=codes_divisions)
		# TODO on teste si divisions est vide ?

		groupe, _ = Groupe.objects.update_or_create(
				nom=code_structure,
				annee=annee_actuelle,
				defaults={
					'nom': code_structure,
					'annee': annee_actuelle,
					'slug': slugify('{}-{}'.format(annee_actuelle,
						code_structure)),
					'mode': Groupe.MODE_AUTOMATIQUE,
					})

		creer_enseignements(classes, groupe, groupe_et, dict_profs)

def import_structures(structures_xml):
	"""Import du fichier Structures.xml"""
	structures_et = ET.parse(structures_xml)
	import_divisions(structures_et.getroot().find('DONNEES/DIVISIONS'))
	import_groupes(structures_et.getroot().find('DONNEES/GROUPES'))

def dict_matieres(matieres_et):
	"""
	Création du dictionnaire des matières à partir d'un fragment XML

	Cette fonction prend en paramètre un sous-arbre etree qui correspond
	à du XML de la forme :

    <MATIERES>
      <MATIERE CODE_MATIERE="001700">
        <CODE_GESTION>CULGE</CODE_GESTION>
        <LIBELLE_COURT>CULTURE GENERALE</LIBELLE_COURT>
        <LIBELLE_LONG>CULTURE GENERALE</LIBELLE_LONG>
        <LIBELLE_EDITION>Culture generale</LIBELLE_EDITION>
        <MATIERE_ETP>1</MATIERE_ETP>
      </MATIERE>
      <MATIERE CODE_MATIERE="002300">
        <CODE_GESTION>TPE</CODE_GESTION>
        <LIBELLE_COURT>TRAVX PERSO.ENCADRES</LIBELLE_COURT>
        <LIBELLE_LONG>TRAVAUX PERSONNELS ENCADRES</LIBELLE_LONG>
        <LIBELLE_EDITION>Travaux personnels encadrés</LIBELLE_EDITION>
        <MATIERE_ETP>0</MATIERE_ETP>
      </MATIERE>
	  ...
	</MATIERES>

	et renvoie le dictionnaire qui à chaque CODE_MATIERE associe un
	dictionnaire dont les clés sont 'code_matiere', 'nom' et
	'virtuelle' (toujours False pour l'instant).

	Un tel fragment XML se retrouve presque à l'identique dans les
	fichiers de nomenclatures SIECLE ou d'emploi du temps STS.
	"""
	# TODO regrouper les LV dans une matière parent
	matieres = {}
	for matiere in matieres_et.findall('MATIERE'):
		if 'CODE_MATIERE' in matiere.attrib:
			code_matiere = matiere.attrib['CODE_MATIERE']
		elif 'CODE' in matiere.attrib:
			code_matiere = matiere.attrib['CODE']
		else:
			continue

		matieres[code_matiere] = {
				'code_matiere': code_matiere,
				'nom': matiere.find('LIBELLE_EDITION').text,
				'virtuelle': False,
				}
	return matieres

def import_mefs(mefs_et):
	"""
	Import des Modules Élémentaires de Formation

	Cette fonction prend en paramètre un sous-arbre etree qui correspond
	à un fragment XML de la forme :
	<MEFS>
	  <MEF CODE="30112013210">
	    <FORMATION>1HEC-E</FORMATION>
	    <LIBELLE_LONG>CPGE1  ECO.ET COMMERC.OPT ECONOMIQUE</LIBELLE_LONG>
	    <LIBELLE_EDITION>Cpge1  eco.et commerc.opt economique</LIBELLE_EDITION>
	  </MEF>
	  <MEF CODE="30112012210">
	    <FORMATION>1HEC-S</FORMATION>
	    <LIBELLE_LONG>CPGE1  ECO.ET COMMERC.OPT SCIENTIFIQUE</LIBELLE_LONG>
	    <LIBELLE_EDITION>Cpge1  eco.et commerc.opt scientifique</LIBELLE_EDITION>
	  </MEF>
	  ...
	</MEFS>

	Elle crée ou met à jour les instances correspondantes dans la base
	de données.

	Elle renvoie le dictionnaire qui à chaque code MEF associe son
	instance ModuleElementaireFormation.
	"""
	mefs = {}

	for mef_et in mefs_et.findall('MEF'):
		if 'CODE_MEF' in mef_et.attrib:
			code_mef = CodeMEF(mef_et.attrib['CODE_MEF'])
		elif 'CODE' in mef_et.attrib:
			code_mef = CodeMEF(mef_et.attrib['CODE'])
		else:
			continue

		if not code_mef.est_superieur():
			continue

		mef_data = {'code_mef': str(code_mef),}

		# La version SIECLE ne possède pas toujours le tag LIBELLE_EDITION
		if mef_et.find('LIBELLE_EDITION') is not None:
			mef_data['libelle'] = mef_et.find('LIBELLE_EDITION').text

		mef, _ = ModuleElementaireFormation.objects.update_or_create(
				code_mef=str(code_mef), defaults=mef_data)

		# En revanche, l'import SIECLE comporte plus souvent un
		# LIBELLE_LONG, que l'on utilise si le MEF n'a toujours pas de
		# libelle.
		if not mef.libelle and mef_et.find('LIBELLE_LONG') is not None:
			mef.libelle = mef_et.find('LIBELLE_LONG').text
			mef.save()

		mefs[str(code_mef)] = mef
	
	return mefs

def import_programmes(programmes_et, matieres):
	for programme in programmes_et.findall('PROGRAMME'):
		code_mef = programme.find('CODE_MEF').text
		if not ModuleElementaireFormation.objects.filter(code_mef=code_mef).exists():
			continue

		# On crée ou on met à jour la matière en base de données
		code_matiere = programme.find('CODE_MATIERE').text

		matiere, _ = Matiere.objects.update_or_create(
				code_matiere=code_matiere,
				defaults=matieres[code_matiere])

		#est_option = (programme.find('CODE_MODALITE_ELECT').text in ('O', 'F'))
		#est_specialite = (programme.find('CODE_MODALITE_ELECT').text == 'O')

		# TODO Ajout à l'objet MEF

		#for classe in classe_par_mef[code_mef]:
		#	enseignement, _ = Enseignement.objects.update_or_create(matiere=matiere,
		#			groupe=classe, defaults={
		#				'option': est_option,
		#				'specialite': est_specialite,
		#				})
		#	# Django ne crée pas de doublon en cas d'un nouvel ajout
		#	classe.enseignements.add(enseignement)

def import_nomenclature_base(nomenclature_et):
	"""
	Cette fonction importe les Modules Élementaires de Formation, les
	matières et les programmes depuis un fichier XML.

	Elle attend en paramètre un fragment d'arbre etree qui correspond à
	une balise XML (peu importe son nom) qui doit contenir trois
	enfants :
	  <MEFS/>
	  <MATIERES/>
	  <PROGRAMMES/>

	Ceci se trouve par exemple dans la balise <NOMENCLATURES/> de
	l'export STS emploi du temps, ou encore dans la balise <DONNEES/> de
	l'export nomenclature de SIECLE.

	L'export nomenclature de SIECLE est plus précis car il indique de
	quelle manière rattacher les options aux classes (obligatoires ou
	non, rang de l'option).

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons : elle met à jour les données si elles existent déjà dans
	la base.
	"""
	matieres = dict_matieres(nomenclature_et.find('MATIERES'))
	import_mefs(nomenclature_et.find('MEFS'))
	import_programmes(nomenclature_et.find('PROGRAMMES'), matieres)

def import_nomenclatures(nomenclatures_xml):
	"""Import des nomenclatures des classes à partir du fichier
	Nomenclatures.xml

	Cette fonction peut être exécutée plusieurs fois sans créer de
	doublons. Elle renseigne dans la base de données les modules
	élémentaires de formation et les matières associées.
	"""
	nomenclatures_et = ET.parse(nomenclatures_xml)

	import_nomenclature_base(nomenclatures_et.getroot().find('DONNEES'))

	## On construit le dictionnaire qui à chaque code MEF associe la
	## liste des classes relevant de ce code.
	#annee_actuelle = Annee.actuelle.all().first()
	#classe_par_mef = {}
	#for classe in Classe.objects.filter(annee=annee_actuelle):
	#	if not classe.code_mef in classe_par_mef:
	#		classe_par_mef[classe.code_mef] = []

	#	classe_par_mef[classe.code_mef].append(classe)

	# TODO créer objets MEF

	# On parcourt ensuite la liste des programmes et on attache chaque
	# matière aux classe possédant le code MEF indiqué pour la matière.

	# TODO mutualiser avec l'import sts_emp qui est moins complet mais
	# qui existe tout de même.

def import_stsemp(stsemp_xml):
	"""
	Import des services et des professeurs depuis STSWEB
	"""
	stsemp_et = ET.parse(stsemp_xml)

	# Construire le dictionnaire des enseignants
	dict_profs = {}
	for individu in stsemp_et.getroot().findall('DONNEES/INDIVIDUS/INDIVIDU'):
		individu_id = individu.attrib['ID']
		nom = individu.find('NOM_USAGE').text.title()
		prenom = individu.find('PRENOM').text.title()

		sexe_xml = individu.find('SEXE').text
		if sexe_xml == '1':
			sexe = User.SEXE_HOMME
		else:
			sexe = User.SEXE_FEMME

		fonction = individu.find('FONCTION').text

		if individu.find('GRADE'):
			grade_xml = individu.find('GRADE').text
		else:
			grade_xml = None

		# TODO quel est le grade pour la classe exceptionnelle des
		# certifiés ?
		if grade_xml == "CERT. H CL" or grade_xml == "CERT. CL N":
			grade = Professeur.CORPS_CERTIFIE
		elif grade_xml == "AGREGE CE" or grade_xml == "AGREGE HCL" or \
				grade_xml == "AGREGE CLN":
			grade = Professeur.CORPS_AGREGE
		elif grade_xml == "CHAIRE SUP":
			grade = Professeur.CORPS_CHAIRESUP
		else:
			grade = Professeur.CORPS_AUTRE

		# XXX La recherche n'est absolument pas robuste aux homonymes
		if fonction == "ENS":
			dict_profs[individu_id], _ = Professeur.objects.update_or_create(
					last_name=nom,
					first_name=prenom,
					defaults={
						'last_name': nom,
						'first_name': prenom,
						'corps': grade,
						'sexe': sexe,
						})
		elif fonction == "DIR":
			User.objects.update_or_create(
					last_name=nom,
					first_name=prenom,
					defaults={
						'last_name': nom,
						'first_name': prenom,
						'sexe': sexe,
						})

	# Mise à jour des programmes, matières et MEF
	import_nomenclature_base(stsemp_et.getroot().find('NOMENCLATURES'))

	# Services d'enseignement dans les classes complètes
	import_divisions(stsemp_et.getroot().find('DONNEES/STRUCTURE/DIVISIONS'),
			dict_profs)

	# Services d'enseignement dans des groupes
	import_groupes(stsemp_et.getroot().find('DONNEES/STRUCTURE/GROUPES'),
			dict_profs)
