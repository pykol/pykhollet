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

from itertools import chain
import xml.etree.ElementTree as ET
import datetime
import re
from collections import defaultdict, namedtuple

from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db import transaction

import isodate
import pytz

from pykol.models.base import User, Etudiant, Professeur, \
		Annee, Classe, Etablissement, Academie, \
		Groupe, Matiere, Enseignement, Service, \
		ModuleElementaireFormation, MEFMatiere, \
		GroupeEffectif, \
		Discipline, OptionEtudiant
from pykol.models.comptabilite import Compte
from pykol.models.colles import CollesEnseignement
from pykol.models.base import ImportBeeLog

class CodeMEF:
	"""
	Gestion d'un code de Module Élémentaire de Formation

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

def parse_datetime_francaise(date):
	"""
	Renvoie un datetime.datetime à partir d'une chaine de caractères
	représentant un instant au format français :
	  DD/MM/YYYY HH:MM:SS
	"""
	mo = re.fullmatch(r'(?P<day>\d+)/(?P<month>\d+)/(?P<year>\d+) (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)',
			date)
	if not mo:
		return None

	vals = mo.groupdict()
	for key in vals:
		vals[key] = int(vals[key])
	vals['tzinfo'] = pytz.timezone('Europe/Paris')

	return datetime.datetime(**vals)

def appartenance_mef_cpge(mef_appartenance_et):
	"""
	Fonction qui recherche si l'un des codes MEF est celui d'une CPGE

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

class BEEImporter:
	"""
	Classe qui gère l'import des données depuis les fichiers XML
	provenant de SIECLE et STS
	"""

	def __init__(self, *xmls):
		"""
		Prend en paramètre les fichiers XML à importer (déjà ouverts) et
		auto-détecte le type de ces fichiers pour réaliser l'import.

		Cette fonction lève une exception ValueError si l'un des
		fichiers donné en argument ne correspond pas au format attendu
		(XML invalide ou bien balise racine ne faisant pas partie de la
		liste des balises gérées).
		"""
		fichiers_invalides = []
		self.structures_et = self.nomenclatures_et = \
				self.eleves_et = self.sts_et = \
				self.nomenclatures_colles_et = None
		for xml in xmls:
			try:
				xml_et = ET.parse(xml)
			except ET.ParseError:
				fichiers_invalides.append(ValueError('xml-invalide', xml))
				continue

			# Auto-détection du type de fichier
			# TODO: pour tous les fichiers sauf STS-EDT, la balise
			# racine possède une indication de version dans l'attribut
			# VERSION, que l'on devrait vérifier.
			# TODO vérifier que l'on ne donne pas plusieurs fois le même
			# type de fichier
			xml_root = xml_et.getroot()
			if xml_root.tag == 'BEE_STRUCTURES':
				# Testé en version 2.0
				self.structures_et = xml_et
			elif xml_root.tag == 'BEE_NOMENCLATURES':
				# Testé en version 3.1
				self.nomenclatures_et = xml_et
			elif xml_root.tag == 'BEE_ELEVES':
				# Testé en version 3.0
				self.eleves_et = xml_et
			elif xml_root.tag == 'STS_EDT':
				self.sts_et = xml_et
			elif xml_root.tag == 'pykol_nomenclatures':
				self.nomenclature_colles_et = xml_et
			else:
				fichiers_invalides.append(ValueError('type-inconnu', xml))

		if fichiers_invalides:
			if len(fichiers_invalides) == 1:
				raise fichiers_invalides[0]
			else:
				raise ValueError(fichiers_invalides)

		### On initialise les champs qui seront peuplés lors de
		### l'import.
		self.annee = self.etablissement = None

		# Dictionnaire qui à chaque code étudiant associe son objet
		# Etudiant. Il est peuplé par l'appel à import_etudiants().
		self.etudiants = {}

		# Dictionnaire qui à chaque code MEF associe son objet
		# ModuleElementaireFormation. Il est peuplé par l'appel à
		# import_mefs().
		self.mefs = {}

		# Dictionnaire qui à chaque code structure de classe associe son
		# objet Classe. Il est peuplé par l'appel à import_divisions().
		self.classes = {}
		# Le même avec les groupes
		self.groupes = {}

		# Dictionnaire qui à chaque code matière associe son objet
		# Matière. Il est peuplé par l'appel à import_programmes().
		self.matieres = {}

		self.professeurs = {}

	def full_import(self):
		"""
		Réalise toutes les étapes d'importation des données.
		"""
		self.import_etablissement()
		self.import_annee()
		self.import_mefs()
		self.import_programmes()
		self.import_professeurs()
		self.import_divisions()
		self.import_groupes()
		self.import_etudiants()
		self.import_options_etudiants()
		self.import_colles()

		self.log_imports()

	def log_imports(self):
		"""
		Enregistre dans la base de données la date d'import des données.
		"""
		fichiers = (
			{
				'field': 'structures_et',
				'type': ImportBeeLog.IMPORT_TYPE_STRUCTURES,
			},
			{
				'field': 'nomenclatures_et',
				'type': ImportBeeLog.IMPORT_TYPE_NOMENCLATURES,
			},
			{
				'field': 'eleves_et',
				'type': ImportBeeLog.IMPORT_TYPE_BASE_ELEVES,
			},
			{
				'field': 'sts_et',
				'type': ImportBeeLog.IMPORT_TYPE_STS,
			},
			{
				'field': 'nomenclatures_colles_et',
				'type': ImportBeeLog.IMPORT_TYPE_COLLES,
			},
		)
		for fichier in fichiers:
			try:
				xml_et = getattr(self, fichier['field'])
				if xml_et is None:
					continue

				log = ImportBeeLog(
					date_import=timezone.now(),
					import_type=fichier['type'],
					annee=self.annee,
				)
				try:
					log.date_fichier = parse_datetime_francaise(xml_et.getroot().find('PARAMETRES/HORODATAGE').text)
				except:
					log.date_fichier = timezone.now()
				log.save()
			except:
				continue

	def import_annee(self):
		"""
		Détermine l'année scolaire à partir des fichiers fournis, et la
		crée si nécessaire (ceci n'est possible qu'avec le fichier STS).

		Cette fonction lève une exception ValueError si l'année ne peut
		pas être déterminée car elle est incohérente entre les fichiers
		fournis, ou bien si elle n'existe pas en base de données et
		qu'elle ne peut pas être créée car le fichier STS est manquant.
		"""
		if self.sts_et:
			annee_et = self.sts_et.getroot().find('PARAMETRES/ANNEE_SCOLAIRE')
			annee_fichier = annee_et.attrib['ANNEE']
			debut = isodate.parse_date(annee_et.find('DATE_DEBUT').text)
			fin = isodate.parse_date(annee_et.find('DATE_FIN').text)
			self.annee, _ = Annee.objects.update_or_create(
					nom=annee_fichier,
					defaults={'debut': debut, 'fin': fin})

		annee_erreurs = []
		for xml_siecle in (self.structures_et, self.nomenclatures_et,
				self.eleves_et):
			if xml_siecle is None:
				continue
			annee_fichier = xml_siecle.getroot().find('PARAMETRES/ANNEE_SCOLAIRE').text
			if self.annee:
				if annee_fichier != self.annee.nom:
					annee_erreurs.append(ValueError('annee-mismatch',
						xml_siecle))
			else:
				try:
					self.annee = Annee.objects.get(nom=annee_fichier)
				except Annee.DoesNotExist:
					annee_erreurs.append(ValueError('annee-inexistante',
						xml_siece))

		if annee_erreurs:
			raise ValueError(annee_erreurs)

		# On tente de synchroniser les vacances si on connait l'académie
		# via l'établissement.
		try:
			self.annee.synchro_vacances(self.etablissement.academie)
		except:
			pass

	def import_etablissement(self):
		"""
		Import des données de l'établissement à partir de la balise <UAJ> de
		l'export STS-EMP.
		"""
		# Le fichier STS permet de créer l'établissement s'il n'existe
		# pas
		if self.sts_et:
			uaj_xml = self.sts_et.getroot().find('PARAMETRES/UAJ')
			academie = Academie.objects.get(pk=int(uaj_xml.find('ACADEMIE/CODE').text))
			denomination = "{} {}".format(
				uaj_xml.find('DENOM_PRINC'),
				uaj_xml.find('DENOM_COMPL'),
			)

			etab_data = {
				'numero_uai': uaj_xml.attrib['CODE'],
				'denomination': denomination,
				'academie': academie,
			}
			self.etablissement, _ = Etablissement.objects.update_or_create(
				numero_uai=etab_data['numero_uai'],
				defaults=etab_data)

		etab_erreurs = []
		for xml_siecle in (self.structures_et, self.nomenclatures_et,
				self.eleves_et):
			if xml_siecle is None:
				continue

			etab_fichier = xml_siecle.getroot().find('PARAMETRES/UAJ').text
			if self.etablissement:
				if etab_fichier != self.etablissement.numero_uai:
					etab_erreurs.append(ValueError('etab-mismatch',
						xml_siecle))
			else:
				try:
					self.etablissement = Etablissement.objects.get(numero_uai=etab_fichier)
				except Etablissement.DoesNotExist:
					etab_erreurs.append(ValueError('etab-inexistant',
						xml_siecle))

		if etab_erreurs:
			raise ValueError(etab_erreurs)

		if not self.etablissement:
			raise ValueError('etab-inconnu')

	def import_mefs(self):
		"""
		Import des Modules Élémentaires de Formation

		Cette fonction prend en paramètre un sous-arbre etree qui correspond
		à un fragment XML de la forme (version STS) :
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

		Elle accepte également la version SIECLE Nomenclatures où
		l'attribut CODE est remplacé par CODE_MEF.

		Elle crée ou met à jour les instances correspondantes dans la base
		de données.

		Elle met à jour le dictionnaire self.mefs qui à chaque code MEF
		associe son instance ModuleElementaireFormation.
		"""
		# Les données se trouvent dans STS ou dans Nomenclatures.
		if self.nomenclatures_et:
			mefs_nomenclatures_et = \
				self.nomenclatures_et.getroot().findall('DONNEES/MEFS/MEF')
		else:
			mefs_nomenclatures_et = []

		if self.sts_et:
			mefs_sts_et = self.sts_et.findall('NOMENCLATURES/MEFS/MEF')
		else:
			mefs_sts_et = []

		# On construit le dictionnaire qui à chaque code MEF contient
		# les informations qui serviront à mettre à jour la base de
		# données
		mefs_dict = {}
		for mef_et in chain(mefs_nomenclatures_et, mefs_sts_et):
			if 'CODE_MEF' in mef_et.attrib:
				code_mef = CodeMEF(mef_et.attrib['CODE_MEF'])
			elif 'CODE' in mef_et.attrib:
				code_mef = CodeMEF(mef_et.attrib['CODE'])
			else:
				continue

			if not code_mef.est_superieur():
				continue

			mef_data = mefs_dict.setdefault(str(code_mef), {})

			# La version SIECLE ne possède pas toujours le tag LIBELLE_EDITION
			if mef_et.find('LIBELLE_EDITION') is not None:
				mef_data.setdefault('libelle',
						mef_et.find('LIBELLE_EDITION').text)
			# En revanche, l'import SIECLE comporte plus souvent un
			# LIBELLE_LONG, que l'on utilise si le MEF n'a toujours pas de
			# libelle.
			elif mef_et.find('LIBELLE_LONG') is not None:
				mef_data.setdefault('libelle',
						mef_et.find('LIBELLE_LONG').text)

		# On crée à présent tous les MEFs dans la base de données
		self.mefs = {}
		with transaction.atomic():
			for code_mef, mef_data in mefs_dict.items():
				mef, _ = ModuleElementaireFormation.objects.update_or_create(
					code_mef=code_mef, defaults=mef_data)
				self.mefs[code_mef] = mef

		# Si personne n'a été importé, on charge simplement la liste des
		# MEFs depuis la base de données.
		if not self.mefs:
			self.mefs = dict([(mef.code_mef, mef) for mef in
				ModuleElementaireFormation.objects.all()])

	def _stocker_services(self, groupe_et, code_div, code_groupe):
		"""
		Crée dans la base de données les objets Service qui se trouvent
		dans le groupe ou la division donnée par le fragment groupe_et.

		Cette méthode crée les objets Enseignement associés aux classes
		s'il n'en existe aucun déjà existant dans la base de données.
		Sinon, elle tente de réutiliser les objets déjà présents (dont
		le groupe n'est pas encore défini).
		"""
		for service_et in groupe_et.findall('SERVICES/SERVICE'):
			code_matiere = service_et.attrib['CODE_MATIERE']

			# On préfère un .filter à un .get car :
			# 1. il arrive que l'administration ne remplisse pas
			#    correctement ses emplois du temps et ajoute des matières
			#    qui ne sont pas dans le programme de la classe (c'est
			#    souvent un cas d'homonymie sur des matières, qui existent
			#    sous plusieurs codes selon les classes) ;
			# 2. on obtient ainsi un itérable, ce qui convient bien au hack
			#    pour la culture générale plus bas, qui manipule deux
			#    matières.

			# Pour la culture générale en ECS/ECE, on fait un petit extra...
			matieres = Matiere.objects.filter(
					Q(code_matiere=code_matiere) |
					Q(parent__virtuelle=True, parent__code_matiere=code_matiere),
				virtuelle=False
			)

			# Pour l'instant, on ne se préoccupe que des cours généraux, la
			# bonne solution serait de se contenter des programmes dans la
			# nomenclature.
			if service_et.attrib['CODE_MOD_COURS'] != 'CG':
				continue

			codes_enseignants = [x.attrib['ID'] for x in
					service_et.findall('ENSEIGNANTS/ENSEIGNANT')]
			# TODO et si la clé code_prof n'existe pas ?
			profs = [self.professeurs[code_prof] for code_prof in codes_enseignants]

			# Bien souvent, cette boucle ne fait qu'une seule itération.
			# Elle n'en fait deux que pour la culture générale en ECS/ECE
			# (voir plus haut à la définition de matieres).
			for matiere in matieres:
				groupe = self.groupes.get(code_groupe,
						self.classes.get(code_groupe))

				enseignement = Enseignement.objects.filter(
						matiere=matiere,
						classe=self.classes[code_div],
						groupe=groupe).first()
				if enseignement is None:
					enseignement = Enseignement.objects.filter(
							matiere=matiere,
							classe=self.classes[code_div],
							groupe__isnull=True).first()
					if enseignement is None:
						enseignement = Enseignement(
								matiere=matiere,
								classe=self.classes[code_div],
								groupe=groupe)
					else:
						enseignement.groupe = groupe
					enseignement.save()

				for prof in profs:
					# Dernier extra pour la culture générale : on relie le
					# prof de philo à la sous-matière philo et le prof de
					# lettres à la sous-matière lettres.
					disciplines_prof = prof.disciplines.values_list('code',
							flat=True)

					if matiere.code_matiere == '001701' and \
							'L0201' not in disciplines_prof and \
							'L0202' not in disciplines_prof:
						continue
					if matiere.code_matiere == '001702' and \
							'L0100' not in disciplines_prof:
						continue

					Service.objects.update_or_create(
							enseignement=enseignement,
							professeur=prof)

	def import_divisions(self):
		"""
		Import des divisions (classes) à partir du fichier
		Structures.xml ou à partir de STS.

		Cette fonction peut être exécutée plusieurs fois sans créer de
		doublons. Les divisions déjà présentes dans la base de données de
		pyKol seront mises à jour si les informations données dans le
		fichier XML diffèrent.

		Cette fonction écrit les modifications dans la base de données, en
		mettant à jour la table Classe.

		Elle nécessite que les MEFs aient été d'abord importés avec un
		appel à la méthode import_mefs().
		"""
		# Les données se trouvent dans STS ou dans Structures.
		if self.structures_et:
			div_structures_et = self.structures_et.getroot().findall('DONNEES/DIVISIONS/DIVISION')
		else:
			div_structures_et = []

		if self.sts_et:
			div_sts_et = self.sts_et.getroot().findall('DONNEES/STRUCTURE/DIVISIONS/DIVISION')
		else:
			div_sts_et = []

		# Création d'un dictionnaire qui à chaque classe associe les
		# données trouvées dans les fichiers
		div_dict = {}
		for division in chain(div_structures_et, div_sts_et):
			# On ne garde que les classes de l'enseignement supérieur
			code_mef = appartenance_mef_cpge(division.find('MEFS_APPARTENANCE'))
			if not code_mef:
				continue

			mef = self.mefs[str(code_mef)]

			# Le code_structure est l'identifiant unique de la classe dans
			# la base élèves.
			if 'CODE_STRUCTURE' in division.attrib: # Version SIECLE
				code_structure = division.attrib['CODE_STRUCTURE']
			elif 'CODE' in division.attrib: # Version STS
				code_structure = division.attrib['CODE']
			else:
				continue # Curieux, pas de code pour la classe ?

			if code_mef.annee() == 1:
				classe_niveau = Classe.NIVEAU_PREMIERE_ANNEE
			else:
				classe_niveau = Classe.NIVEAU_DEUXIEME_ANNEE

			classe_data = div_dict.setdefault(code_structure, {})

			classe_data.update({
				'mef': mef,
				'slug': slugify("{annee}-{code}".format(annee=self.annee, code=code_structure)),
				'nom': division.find('LIBELLE_LONG').text,
				'niveau': classe_niveau,
				'mode': Groupe.MODE_AUTOMATIQUE,
				'xml': division,
				})

		# On crée à présent les classes dans la base de données
		with transaction.atomic():
			for code_structure, classe_data in div_dict.items():
				classe_xml = classe_data.pop('xml')
				try:
					classe = Classe.all_objects.get(
						code_structure=code_structure,
						annee=self.annee,
						etablissement=self.etablissement)

					for field, value in classe_data.items():
						setattr(classe, field, value)
				except Classe.DoesNotExist:
					classe = Classe(
						code_structure=code_structure,
						annee=self.annee,
						etablissement=self.etablissement,
						**classe_data
					)
					compte_colles = Compte(
						categorie=Compte.CATEGORIE_ACTIFS,
						nom="{classe} - {annee}".format(classe=classe.nom,
							annee=classe.annee.nom),
						parent=classe.etablissement.compte_colles,
					decouvert_autorise=True)
					compte_colles.save()
					classe.compte_colles = compte_colles

				classe.save()

				self.classes[code_structure] = classe

				# L'appel à _stocker_services crée les enseignements qui
				# correspondent à chaque service de professeur. On
				# peuple avant cet appel la base de données avec les
				# enseignements minimaux pour représenter les matières
				# prévues au programme de cette classe.
				for mefmatiere in classe.mef.mefmatiere_set.all():
					if not Enseignement.objects.all().filter(
							classe=classe,
							matiere=mefmatiere.matiere,
							rang_option=mefmatiere.rang_option,
							modalite_option=mefmatiere.modalite_option,
							periode=mefmatiere.periode,
							).exists():
						Enseignement(classe=classe,
							matiere=mefmatiere.matiere,
							rang_option=mefmatiere.rang_option,
							modalite_option=mefmatiere.modalite_option,
							periode=mefmatiere.periode,
							).save()

				# Dans le fichier STS, on peut trouver des services
				# d'enseignement parmi les informations de la division.
				self._stocker_services(classe_xml, code_structure,
						code_structure)

		# Si aucune donnée n'a été importée, on charge les classes
		# depuis la base de données.
		if not self.classes:
			self.classes = dict([(c.code_structure, c)
				for c in Classe.all_objects.filter(annee=self.annee)])

	def import_groupes(self):
		"""
		Création des groupes d'enseignement à partir de l'export STS ou
		du fichier Structures.
		"""
		# Les données se trouvent dans STS ou dans Structures.
		if self.structures_et:
			groupe_structures_et = \
				self.structures_et.getroot().findall('DONNEES/GROUPES/GROUPE')
		else:
			groupe_structures_et = []

		if self.sts_et:
			groupe_sts_et = self.sts_et.getroot().findall('DONNEES/STRUCTURE/GROUPES/GROUPE')
		else:
			groupe_sts_et = []

		# Création d'un dictionnaire qui à chaque groupe associe les
		# données trouvées dans les fichiers
		groupe_dict = {}
		for groupe_et in chain(groupe_structures_et, groupe_sts_et):
			# Récupération du code structure
			if 'CODE_STRUCTURE' in groupe_et.attrib: # Version SIECLE Structures.xml
				code_structure = groupe_et.attrib['CODE_STRUCTURE']
			elif 'CODE' in groupe_et.attrib: # Version STS-EMP
				code_structure = groupe_et.attrib['CODE']
			else:
				continue

			if not appartenance_mef_cpge(groupe_et.find('MEFS_APPARTENANCE')):
				continue

			groupe_data = groupe_dict.setdefault(code_structure, {})

			# L'effectif est présent dans la version STS. On l'importe dans
			# ce cas. Le détail de l'effectif par classe est importé plus
			# bas, une fois que le groupe est créé.
			try:
				groupe_data['effectif_sts'] = int(groupe_et.find('EFFECTIF_PREVU').text)
			except:
				pass

			groupe_data['nom'] = code_structure
			groupe_data['slug'] = slugify('{}-{}'.format(self.annee, code_structure))
			groupe_data['mode'] = Groupe.MODE_AUTOMATIQUE

			groupe, _ = Groupe.objects.update_or_create(
					code_structure=code_structure,
					annee=self.annee,
					defaults=groupe_data)

			self.groupes[code_structure] = groupe

			# On détaille les effectifs du groupe par classe et on
			# stocke les Enseignement qu'il faudra créer.
			divisions_et = groupe_et.findall('DIVISIONS_APPARTENANCE/DIVISION_APPARTENANCE')
			for division_et in divisions_et:
				try:
					# Version STS
					code_div = division_et.attrib['CODE']
				except KeyError:
					# Version SIECLE/Structure
					code_div = division_et.find('CODE_STRUCTURE').text

				classe = self.classes[code_div]
				try:
					effectif_div = int(division_et.find('EFFECTIF_PREVU').text)
				except:
					effectif_div = None

				GroupeEffectif.objects.update_or_create(
						groupe=groupe, classe=classe,
						defaults={'effectif_sts': effectif_div})

				# On stocke les services d'enseignement correspondant à ce
				# groupe et à cette classe.
				self._stocker_services(groupe_et, code_div,
						code_groupe=code_structure)

		# TODO faut-il peupler self.groupes avec la base de données s'il
		# est vide à ce stade de la méthode ?

	def import_etudiants(self):
		"""
		Import de la liste des étudiants à partir de l'export SIECLE

		Cette fonction peut être exécutée plusieurs fois sans créer de
		doublons. Les étudiants déjà présents dans la base de données de
		pyKol seront mis à jour si les informations présentes dans le
		fichier XML diffèrent.

		Les étudiants sont identifiés par leur INE (provenant du RNIE).

		L'import des étudiants doit nécessairement être réalisé après
		l'import des structures, car la création d'un étudiant nécessite de
		le rattacher à une classe déjà existante dans la base de données.
		"""
		if not self.eleves_et:
			return

		# On construit le dictionnaire qui à chaque numéro d'élève
		# associe la classe dans laquelle l'étudiant est inscrit.
		# Ceci permettra de filtrer rapidement plus tard les élèves à
		# importer.
		classe_etudiant = {}
		for struct_eleve in self.eleves_et.getroot().findall('DONNEES/STRUCTURES/STRUCTURES_ELEVE'):
			code_structure = struct_eleve.find('STRUCTURE/CODE_STRUCTURE').text
			num_eleve = struct_eleve.attrib['ELENOET']
			try:
				classe_etudiant[num_eleve] = self.classes[code_structure]
			except:
				# L'étudiant n'est pas dans une classe gérée par pyKol.
				continue

		# On peut à présent créer ou mettre à jour les élèves dans la base de
		# données. Le dictionnaire classe_etudiant permet de mettre la main
		# sur la classe où affecter l'étudiant.
		for eleve in self.eleves_et.getroot().findall('DONNEES/ELEVES/ELEVE'):
			# TODO On regarde si on connait la scolarité de l'an dernier
			#origine = None
			#if eleve.find('SCOLARITE_AN_DERNIER'):
			#	uai_origine = eleve.find('SCOLARITE_AN_DERNIER/CODE_RNE').text
			#	# origine = Etablissement.objects.get(numero_uai=uai_origine)

			num_eleve = eleve.attrib['ELENOET']

			etudiant_data = {}

			try:
				etudiant_data['classe'] = classe_etudiant[num_eleve]
			except:
				# Si l'étudiant n'a pas de classe connue, il se peut
				# qu'il s'agisse d'une démission. Pour le savoir, on
				# regarde s'il était déjà présent dans la base de
				# données.
				if not Etudiant.objects.filter(numero_siecle=num_eleve).exists():
					continue

			etudiant_data['entree'] = parse_date_francaise(eleve.find('DATE_ENTREE').text)

			try:
				etudiant_data['sortie'] = parse_date_francaise(eleve.find('DATE_SORTIE').text)
			except:
				pass

			email_et = eleve.find('MEL')
			if email_et is not None and email_et.text:
				etudiant_data['email'] = email_et.text

			etudiant_data['sexe'] = int(eleve.find('CODE_SEXE').text)
			etudiant_data['first_name'] = eleve.find('PRENOM').text.title()
			etudiant_data['last_name'] = eleve.find('NOM_DE_FAMILLE').text.title()
			etudiant_data['birth_date'] = parse_date_francaise(eleve.find('DATE_NAISS').text)

			# On tente de retrouver l'étudiant avec son INE, et au pire
			# le numéro SIECLE.
			etudiant_data['numero_siecle'] = num_eleve

			if eleve.find('ID_NATIONAL') is None:
				if eleve.find('INE_RNIE') is not None:
					etudiant_data['ine'] = eleve.find('INE_RNIE').text
			else:
				etudiant_data['ine'] = eleve.find('ID_NATIONAL').text

			if etudiant_data.get('ine'):
				self.etudiants[num_eleve], _ = Etudiant.objects.filter(
						Q(ine=etudiant_data['ine']) |
						Q(numero_siecle=etudiant_data['numero_siecle'])
					).update_or_create(defaults=etudiant_data)
			else:
				self.etudiants[num_eleve], _ = Etudiant.objects.filter(
						numero_siecle=etudiant_data['numero_siecle']
					).update_or_create(defaults=etudiant_data)

		# Une fois que tous les étudiants ont été importés, on met à jour
		# les compositions des classes
		for classe in self.classes.values():
			classe.update_etudiants()

	@transaction.atomic
	def import_options_etudiants(self):
		"""
		Import des options suivies par chaque étudiant à partir de
		l'export SIECLE de la liste des élèves.
		"""
		if not self.eleves_et:
			return

		# Représentation temporaire des options afin de comparer la
		# liste de celles présentes dans SIECLE avec celles présentes
		# dans la base de données.
		SiecleOption = namedtuple('SiecleOption', ['rang', 'modalite',
			'matiere'])

		for eleve_et in self.eleves_et.getroot().findall('DONNEES/OPTIONS/OPTION'):
			try:
				etudiant = self.etudiants[eleve_et.attrib['ELENOET']]
			except:
				continue

			# On commence par faire la liste des options présentes dans
			# le fichier SIECLE.
			options_siecle = set()
			for option_et in eleve_et.findall('OPTIONS_ELEVE'):
				options_siecle.add(SiecleOption(
					rang=int(option_et.find('NUM_OPTION').text),
					modalite=OptionEtudiant.parse_modalite_election(
						option_et.find('CODE_MODALITE_ELECT').text),
					matiere=self.matieres[option_et.find('CODE_MATIERE').text]
				))

			# On obtient ensuite la liste des options présentes dans la
			# base de données.
			options_db = set()
			for option_db in OptionEtudiant.objects.filter(etudiant=etudiant,
					classe=etudiant.classe):
				options_db.add(SiecleOption(
					rang=option_db.rang_option,
					modalite=option_db.modalite_option,
					matiere=option_db.matiere.code_matiere,
				))

			# On supprime les options qui ont disparu de SIECLE
			for option_suppr in options_db.difference(options_siecle):
				OptionEtudiant.objects.filter(etudiant=etudiant,
					classe=etudiant.classe,
					rang_option=option_suppr.rang,
					modalite_option=option_suppr.modalite,
					matiere__code_matiere=option_suppr.matiere).delete()

			# On ajoute les options qui n'étaient pas présentes dans la
			# base de données.
			for option_add in options_siecle.difference(options_db):
				OptionEtudiant(
					etudiant=etudiant,
					classe=etudiant.classe,
					rang_option=option_add.rang,
					modalite_option=option_add.modalite,
					matiere=option_add.matiere).save()

	def _dict_matieres(self):
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
		# Les données se trouvent dans STS ou dans Structures.
		if self.nomenclatures_et:
			div_nomenclatures_et = \
				self.nomenclatures_et.getroot().findall('DONNEES/MATIERES/MATIERE')
		else:
			div_nomenclatures_et = []

		if self.sts_et:
			div_sts_et = self.sts_et.getroot().findall('NOMENCLATURES/MATIERES/MATIERE')
		else:
			div_sts_et = []

		matieres = {}
		for matiere in chain(div_nomenclatures_et, div_sts_et):
			if 'CODE_MATIERE' in matiere.attrib:
				code_matiere = matiere.attrib['CODE_MATIERE']
			elif 'CODE' in matiere.attrib:
				code_matiere = matiere.attrib['CODE']
			else:
				continue

			nom_matiere = matiere.find('LIBELLE_EDITION').text

			# On regroupe les langues dans une même matière parent. On
			# identifie les groupes de matières avec les deux derniers
			# chiffres du code matière. Ils sont en général nuls, sauf pour
			# les langues où toutes les LV1 se retrouvent par exemple sous
			# un code de la forme 03xx01.
			# Le nom de la matière générique est choisi en prenant la plus
			# longue sous-chaine commune (algorithme non optimal de
			# programmation dynamique ici, les chaines sont peu nombreuses
			# et de petite taille).
			# Le code de la matière générique est de la forme xx00xx, où on
			# remplace la partie entre les différentes sous-matières par 00.
			def longest_common_substring(s1, s2):
				m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
				longest, x_longest = 0, 0
				for x in range(1, 1 + len(s1)):
					for y in range(1, 1 + len(s2)):
						if s1[x - 1] == s2[y - 1]:
							m[x][y] = m[x - 1][y - 1] + 1
							if m[x][y] > longest:
								longest = m[x][y]
								x_longest = x
						else:
							m[x][y] = 0
				return s1[x_longest - longest: x_longest]

			if code_matiere[-2:] != "00":
				code_parent = code_matiere[0:2] + "00" + code_matiere[4:6]
				try:
					nom_parent = longest_common_substring(nom_matiere.upper(),
							matieres[code_parent]['nom'])
				except:
					nom_parent = nom_matiere.upper()

				matieres[code_parent] = {
						'code_matiere': code_parent,
						'nom': nom_parent,
						'virtuelle': True,
				}
			else:
				code_parent = None

			# Exception pour la culture générale en ECS/ECE, qui possède le
			# code 001700 et que l'on découpe artificiellement en deux
			# sous-matières 001701 (culture générale - lettres) et 001702
			# (culture générale - philosophie).
			if code_matiere == '001700':
				code_lettres = code_matiere[:4] + '01'
				code_philo   = code_matiere[:4] + '02'
				matieres[code_lettres] = {
						'code_matiere': code_lettres,
						'nom': "Lettres",
						'virtuelle': False,
						'code_parent': code_matiere
					}
				matieres[code_philo] = {
						'code_matiere': code_philo,
						'nom': "Philosophie",
						'virtuelle': False,
						'code_parent': code_matiere
					}
				matiere_virtuelle = True
			else:
				matiere_virtuelle = False

			matieres[code_matiere] = {
					'code_matiere': code_matiere,
					'nom': matiere.find('LIBELLE_EDITION').text,
					'virtuelle': matiere_virtuelle,
					'code_parent': code_parent,
					}

		return matieres

	def _creer_matiere(self, dict_matieres, code_matiere):
		try:
			matiere = self.matieres[code_matiere]
			return matiere
		except KeyError:
			pass

		try:
			matiere_data = dict_matieres[code_matiere]
		except KeyError:
			# Si le dictionnaire des matières n'est pas renseigné depuis
			# le fichier XML, on tente d'obtenir la matière depuis la
			# base de données. Si cela échoue, on laisse l'exception
			# filer.
			self.matieres[code_matiere] = Matiere.objects.get(code_matiere=code_matiere)
			return self.matieres[code_matiere]

		# Cas de base où le dictionnaire des matières est rempli, et où
		# on doit mettre à jour la base de données.

		# Si nécessaire on construit la matière parent.
		if matiere_data.get('code_parent', None):
			matiere_parent = self._creer_matiere(dict_matieres,
					matiere_data['code_parent'])
		else:
			matiere_parent = None

		dict_matieres[code_matiere].pop('code_parent', None)
		dict_matieres[code_matiere]['parent'] = matiere_parent

		matiere, _ = Matiere.objects.update_or_create(
			code_matiere=code_matiere,
			defaults=dict_matieres[code_matiere])
		self.matieres[code_matiere] = matiere

		# Si la matière est virtuelle, on construit les matières filles
		if matiere.virtuelle:
			filles = [m['code_matiere'] for m in dict_matieres.values()
					if 'code_parent' in m and m['code_parent'] == code_matiere]
			for fille in filles:
				self._creer_matiere(dict_matieres, fille)

		return self.matieres[code_matiere]

	def import_programmes(self):
		"""
		Import du contenu de la balise <PROGRAMMES/> présente dans
		Nomenclatures, qui à chaque code MEF indique les matières
		prévues dans la formation.

		L'information est partiellement présente dans le fichier STS,
		mais incomplète (code modalité élection manquant), donc on ne
		l'importe pas depuis ce fichier.

		Cette fonction crée dans la base de données les matières qui
		correspondent à des formations présentes dans self.mefs (qui
		doit donc avoir été peuplé au préalable par import_mefs())
		et elle met à jour les objets de self.mefs avec la liste de
		leurs matières.
		"""
		# Les données sont dans Nomenclature.
		if not self.nomenclatures_et:
			# On remplit le dictionnaire des matières à partir de la
			# base de données, faute d'avoir le fichier XML.
			for matiere in Matiere.objects.all():
				self.matieres[matiere.code_matiere] = matiere
			return

		# On récupère la liste des matières déclarées dans le fichier,
		# pour les créer si nécessaire.
		dict_matieres = self._dict_matieres()

		# On stocke les rangs des options obligatoires.
		rang_option = defaultdict(dict)
		for option_et in \
				self.nomenclatures_et.getroot().findall('DONNEES/OPTIONS_OBLIGATOIRES/OPTION_OBLIGATOIRE'):
			code_mef = option_et.find('CODE_MEF').text
			code_matiere = option_et.find('CODE_MATIERE').text
			rang_option[code_mef][code_matiere] = int(option_et.find('RANG_OPTION').text)

		# On peut ensuite créer les options.
		for programme_et in self.nomenclatures_et.getroot().findall('DONNEES/PROGRAMMES/PROGRAMME'):
			try:
				mef = self.mefs[programme_et.find('CODE_MEF').text]
			except:
				continue

			matiere = self._creer_matiere(dict_matieres,
				programme_et.find('CODE_MATIERE').text)

			modalite_option = MEFMatiere.parse_modalite_election(
					programme_et.find('CODE_MODALITE_ELECT').text)

			defaults = {}
			if modalite_option == MEFMatiere.MODALITE_OBLIGATOIRE:
				defaults['rang_option'] = rang_option[mef.code_mef][matiere.code_matiere]

			if matiere.virtuelle:
				matiere_list = matiere.filles.all()
			else:
				matiere_list = [matiere]
			for matiere in matiere_list:
				# Hack pour la PCSI car les périodes ne sont pas
				# indiquées dans le fichier XML et sont indispensables
				# pour coller aux dotations de colles
				if mef.code_mef == '30111019210':
					# Choix entre option SI et option chimie uniquement
					# en deuxième période. (L'option de rang 1
					# correspond aux langues vivantes.)
					if defaults.get('rang_option', None) == 2:
						defaults['periode'] = MEFMatiere.PERIODE_DEUXIEME

					# Chimie pour l'option SI
					if matiere.code_matiere == '067200':
						defaults['periode'] = MEFMatiere.PERIODE_DEUXIEME

					# SI ou chimie au premier semestre
					if modalite_option == MEFMatiere.MODALITE_FACULTATIVE \
							and matiere.code_matiere in ('067000', '067100'):
						modalite_option = MEFMatiere.MODALITE_COMMUN
						defaults['periode'] = MEFMatiere.PERIODE_PREMIERE

				# Retour au cas général
				MEFMatiere.objects.update_or_create(
					mef=mef, matiere=matiere,
					modalite_option=modalite_option,
					defaults=defaults)


	def import_professeurs(self):
		"""
		Import de la liste des professeurs depuis STS.

		Cette fonction peuple le dictionnaire self.professeurs qui à
		chaque code professeur associe l'objet Professeur correspondant.
		"""
		if not self.sts_et:
			# TODO charger les profs si pas de STS
			return

		for individu in self.sts_et.getroot().findall('DONNEES/INDIVIDUS/INDIVIDU'):
			individu_id = individu.attrib['ID']
			nom = individu.find('NOM_USAGE').text.title()
			prenom = individu.find('PRENOM').text.title()
			numero_sts = individu.attrib.get('ID')

			sexe_xml = individu.find('SEXE').text
			if sexe_xml == '1':
				sexe = User.SEXE_HOMME
			else:
				sexe = User.SEXE_FEMME

			fonction = individu.find('FONCTION').text

			if individu.find('GRADE') is not None:
				grade_xml = individu.find('GRADE').text
			else:
				grade_xml = None

			if grade_xml == "CERT CE" or grade_xml == "CERT. H CL" or \
					grade_xml == "CERT. CL N":
				grade = Professeur.CORPS_CERTIFIE
			elif grade_xml == "AGREGE CE" or grade_xml == "AGREGE HCL" or \
					grade_xml == "AGREGE CLN":
				grade = Professeur.CORPS_AGREGE
			elif grade_xml == "CHAIRE SUP":
				grade = Professeur.CORPS_CHAIRESUP
			else:
				grade = Professeur.CORPS_AUTRE

			# XXX La recherche n'est absolument pas robuste aux homonymes,
			# mais les fichiers XML de STS ne donnent pour identifiant
			# qu'une clé primaire opaque, non documentée et probablement
			# instable avec le temps.
			if fonction == "ENS":
				# Construction de la liste des disciplines du
				# professeur.
				# On calcule aussi le nombre d'heures pour tenter de
				# deviner le code indemnité à appliquer pour les colles.
				# Ce n'est qu'une approximation : on obtient via STS
				# l'ORS. On va considérer que des ORS de 8h, 9h, 10, 11h
				# sont des ORS de CPGE et appliquer l'indemnité de CPGE
				# pour les colles. Le vrai critère vient du service, qui
				# doit être effectué pour plus de la moitié en CPGE.
				# Mais ceci ne peut pas être deviné via STS. L'algo
				# appliqué ici ne marche pas dans un paquet de
				# situations (temps partiel, service partagé). Il ne
				# donne qu'une première approximation qui doit être
				# confirmée manuellement par le secrétariat.

				disciplines = []
				nb_heures = 0
				for discipline_et in individu.findall('DISCIPLINES/DISCIPLINE'):
					discipline, _ = Discipline.objects.get_or_create(
							code=discipline_et.attrib['CODE'],
							defaults={'nom': discipline_et.find('LIBELLE_COURT').text})
					disciplines.append(discipline)
					nb_heures += float(discipline_et.find('NB_HEURES').text)

				# Comme dit plus haut, ceci n'est qu'une vague
				# approximation.
				est_prof_cpge = 8 <= nb_heures <= 11

				# On ne peut pas utiliser la méthode
				# Professeur.objects.update_or_create car il faut
				# initialiser les colles de comptes de colles du
				# professeur.
				try:
					professeur = Professeur.objects.get(
						last_name=nom,
						first_name=prenom,
						sexe=sexe)

					professeur.etablissement = self.etablissement
					professeur.corps = grade
					professeur.id_acad = numero_sts
					if est_prof_cpge:
						professeur.code_indemnite = professeur.CODE_INDEMNITE_PROF_CPGE
					professeur.save()

				except Professeur.DoesNotExist:
					professeur = Professeur.objects.create(
						last_name=nom,
						first_name=prenom,
						sexe=sexe,
						etablissement=self.etablissement,
						corps=grade,
						id_acad=numero_sts,
						code_indemnite = professeur.CODE_INDEMNITE_PROF_CPGE if est_prof_cpge
							else professeur.CODE_INDEMNITE_PROF_AUTRE,
						)

				professeur.disciplines.set(disciplines)
				self.professeurs[individu_id] = professeur

			elif fonction == "DIR":
				user, _ = User.objects.update_or_create(
						last_name=nom,
						first_name=prenom,
						defaults={
							'last_name': nom,
							'first_name': prenom,
							'sexe': sexe,
							})
				perm_direction = Permission.objects.get(codename='direction',
						content_type=ContentType.objects.get_for_model(User))
				user.user_permissions.add(perm_direction)

		# TODO charger les profs si pas de sts


	def import_colles(self):
		if not self.nomenclature_colles_et:
			return

		for colle_et in self.nomenclature_colles_et.getroot().findall('colles/colle'):
			nomenclature_id = colle_et.attrib['id']
			mefs = [x.text for x in colle_et.findall('codes_mefs/code_mef')]
			matieres = [x.text for x in colle_et.findall('codes_matieres/code_matiere')]
			duree = isodate.parse_duration(colle_et.find('duree').text)

			periode_et = colle_et.find('periode')
			if periode_et is None:
				periode = CollesEnseignement.PERIODE_ANNEE
			elif periode_et.text == 'premiere_periode':
				periode = CollesEnseignement.PERIODE_PREMIERE
			elif periode_et.text == 'deuxieme_periode':
				periode = CollesEnseignement.PERIODE_DEUXIEME

			try:
				nom_enveloppe = colle_et.find('nom').text
			except:
				nom_enveloppe = ''

			frequence_text = colle_et.find('frequence').text
			if frequence_text == 'hebdomadaire':
				frequence = CollesEnseignement.FREQUENCE_HEBDOMADAIRE
			elif frequence_text == 'trimestrielle':
				frequence = CollesEnseignement.FREQUENCE_TRIMESTRIELLE

			mode_defaut = CollesEnseignement.MODE_INTERROGATION
			try:
				if colle_et.find('mode_defaut').text == 'travaux_diriges':
					mode_defaut = CollesEnseignement.MODE_TD
			except:
				pass

			for classe in Classe.all_objects.filter(mef__code_mef__in=mefs,
					annee=self.annee):
				enseignements = Enseignement.objects.filter(
					Q(classe=classe),
					Q(
						Q(matiere__code_matiere__in=matieres) |
						Q(matiere__parent__code_matiere__in=matieres)
					)
				).distinct()

				if periode == CollesEnseignement.PERIODE_PREMIERE:
					enseignements = enseignements.exclude(periode=Enseignement.PERIODE_DEUXIEME)
				elif periode == CollesEnseignement.PERIODE_DEUXIEME:
					enseignements = enseignements.exclude(periode=Enseignement.PERIODE_PREMIERE)

				# On n'ajoute la dotation que si l'on a les enseignements
				# correspondants.
				if enseignements:
					try:
						colles_ens = CollesEnseignement.objects.get(
							nomenclature_id=nomenclature_id,
							classe=classe)
					except CollesEnseignement.DoesNotExist:
						colles_ens = CollesEnseignement(
							nomenclature_id=nomenclature_id,
							classe=classe,
							nom=nom_enveloppe,
							frequence=frequence,
							duree_frequentielle=duree,
							periode=periode,
							mode_defaut=mode_defaut
						)
						compte_colles = Compte(
							categorie=Compte.CATEGORIE_ACTIFS,
							nom=colles_ens.meilleure_matiere_enseignements(enseignements),
							parent=colles_ens.classe.compte_colles,
							decouvert_autorise=True)
						compte_colles.save()
						colles_ens.compte_colles = compte_colles
						colles_ens.save()

					colles_ens.enseignements.set(enseignements)
