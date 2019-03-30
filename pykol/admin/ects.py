# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
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

import os
import xml.etree.ElementTree as ET

from django.contrib import admin
from django.db.models import Q
from django.conf import settings

from pykol.admin.base import register, admin_site
from pykol.models.ects import Jury, Mention, Grille, GrilleLigne, \
		GrilleGroupeLignes, GrilleMatchLigne
from pykol.models.base import ModuleElementaireFormation, MEFMatiere

admin_site.register(Jury)

class GrilleLigneInline(admin.TabularInline):
	model = GrilleLigne
	ordering = ('groupe__position', 'position',)
	raw_id_fields = ('matiere', 'groupe')
class GrilleMatchLigneInline(admin.TabularInline):
	model = GrilleMatchLigne
	raw_id_fields = ('matiere',)
@register(Grille)
class GrilleAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'semestre')
	inlines = (GrilleLigneInline, GrilleMatchLigneInline)

@register(Mention)
class MentionAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'jury', 'etudiant', 'enseignement')
	list_filter = ('jury',)


PYKOL_NS = 'http://hatat.me/2018/pykol'
def nstag(tagname):
	"""
	Raccourci pour recréer les noms de balises XML qualifiés avec
	l'espace de nom de pyKol, selon le format adopté par ElementTree.
	"""
	return "{{{ns}}}{tag}".format(ns=PYKOL_NS, tag=tagname)

def query_matieres_from_tag(matiere_et, code_mef):
	modalite_option = MEFMatiere.parse_modalite_election(
		matiere_et.attrib.get('modalite_option', 'S'))

	mefmatiere_q = Q(mef=code_mef) & \
		Q(modalite_option=modalite_option)

	if modalite_option != MEFMatiere.MODALITE_COMMUN:
		rang = matiere_et.attrib.get('rang_option')
		if rang is not None:
			mefmatiere_q = mefmatiere_q & Q(rang_option=rang)

	code_matiere = matiere_et.attrib.get('code')
	if code_matiere is not None:
		mefmatiere_q = mefmatiere_q & Q(matiere__code_matiere=code_matiere)

	return MEFMatiere.objects.filter(mefmatiere_q)

def creer_grille_ligne(ligne_et, grille, position=0, groupe=None):
	"""
	Création des GrilleLigne engendrées par la balise <ligne> donnée en
	paramètre.
	"""
	libelle = ligne_et.attrib.get('nom', "")

	for matiere_et in ligne_et.findall(nstag('matiere')):
		matieres = query_matieres_from_tag(matiere_et, grille.code_mef)

		force_creation = (matiere_et.attrib.get('force', 'false') == 'true')
		credits = matiere_et.attrib.get('credits',
				ligne_et.attrib.get('credits', 0))

		for matiere in matieres:
			GrilleLigne.objects.get_or_create(grille=grille,
				groupe=groupe,
				matiere=matiere,
				libelle=libelle,
				defaults={
					'credits': credits,
					'position': position,
					'force_creation': force_creation,
				}
			)

def charger_grilles_xml():
	"""
	Création de toutes les grilles depuis la nomenclature au format XML.
	"""
	xml = os.path.join(settings.BASE_DIR, 'pykol/data/GrillesECTS.xml')
	xml_et = ET.parse(xml).getroot()

	grilles = {}
	for grille_et in xml_et.findall(nstag('grille_ects')):
		grilles[grille_et.attrib['{http://www.w3.org/XML/1998/namespace}id']] = grille_et

	for classe in xml_et.findall(nstag('classe')):
		grille_et = grilles[classe.attrib['grille_ref']]
		grille, _ = Grille.objects.get_or_create(
			ref=classe.attrib['grille_ref'],
			code_mef=ModuleElementaireFormation.objects.get(code_mef=classe.attrib['code_mef']),
			semestre=classe.attrib['semestre'], defaults={})

		# Peupler la grille avec ses lignes
		for position, grille_child in enumerate(grille_et):
			if grille_child.tag == nstag('ligne'):
				creer_grille_ligne(grille_child, grille,
						position=position)

			if grille_child.tag == nstag('groupe'):
				groupe, _ = GrilleGroupeLignes.objects.get_or_create(grille=grille,
						libelle=grille_child.attrib['nom'],
						defaults={'position': position})

				for pos_ligne, ligne_et in enumerate(grille_child.findall(nstag('ligne'))):
					creer_grille_ligne(ligne_et, grille,
							position=pos_ligne, groupe=groupe)

			if grille_child.tag == nstag('match'):
				for matiere_et in grille_child.findall(nstag('matiere')):
					for matiere in query_matieres_from_tag(matiere_et, grille.code_mef):
						GrilleMatchLigne.objects.get_or_create(
							grille=grille,
							matiere=matiere,
							defaults={})
