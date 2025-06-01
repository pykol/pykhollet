# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
# Copyright (C) 2008 Søren Roug, European Environment Agency (odtmerge function, GPLv2)
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
import copy

from django.contrib.auth.decorators import login_required, \
		permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Min

import odf.opendocument
from odf.opendocument import OpenDocumentText
from odf.text import UserFieldDecl, UserFieldGet, Span, P
from odf.table import Table, TableCell, TableRow, CoveredTableCell
from odf.draw import Frame, Image
import odf.namespaces

from pykol.models.ects import Jury, Mention, GrilleGroupeLignes
from pykol.models.base import Etudiant, Enseignement
from pykol.views.generic import OdfResponse

def odtmerge(fromodt, toodt):
	# Need to make a copy of the list because addElement unlinks from the original
	for meta in fromodt.meta.childNodes[:]:
		toodt.meta.addElement(meta)

	for font in fromodt.fontfacedecls.childNodes[:]:
		toodt.fontfacedecls.addElement(font)

	for style in fromodt.styles.childNodes[:]:
		toodt.styles.addElement(style)

	for autostyle in fromodt.automaticstyles.childNodes[:]:
		toodt.automaticstyles.addElement(autostyle)

	for scripts in fromodt.scripts.childNodes[:]:
		toodt.scripts.addElement(scripts)

	for settings in fromodt.settings.childNodes[:]:
		toodt.settings.addElement(settings)

	for masterstyles in fromodt.masterstyles.childNodes[:]:
		toodt.masterstyles.addElement(masterstyles)

    # odfpy ne met pas à jour ses caches. Ceux du document d'origine ont encore
    # trace d'éléments retirés. On force la mise à jour pour contourner (ce qui
    # détruit totalement le contenu de fromodt).
	fromodt.rebuild_caches()
	for body in fromodt.body.childNodes[:]:
		toodt.body.addElement(body)

	toodt.Pictures.update(fromodt.Pictures)

	return toodt


def nom_formation(jury):
	return "{libelle} − {niveau}".format(
		libelle=jury.classe.mef.libelle_ects,
		niveau=jury.classe.get_niveau_display())

def fusion_attestation(attestation, etudiant, jury):
	"""
	Remplace dans un modèle OpenDocument d'attestation de résultats les champs
	utilisateurs par les données de l'étudiant. Cette fonction renvoie le
	document OpenDocument modifié. Le modèle est potentiellement modifié par
	l'appel, il n'est plus utilisable par la suite.
	"""
	remplacement = {
		'pykol.date_naissance_etudiant': etudiant.birth_date.strftime("%d/%m/%Y"),
		'pykol.ine_etudiant': etudiant.ine,
		'pykol.nom_formation': nom_formation(jury),
		'pykol.domaines_etude': jury.classe.mef.domaines_etude,
		'pykol.nom_etudiant': str(etudiant),
		'pykol.nom_etudiant_civilite': etudiant.name_civilite(),
		'pykol.date_attestation': jury.date.strftime("%d/%m/%Y"),
		'pykol.nom_signataire': jury.classe.etablissement.chef_etablissement.name_civilite(),
		'pykol.nom_lycee': jury.classe.etablissement.appellation,
		'pykol.statut_lycee': jury.classe.etablissement.get_nature_uai_display(),
		'pykol.ville_lycee': jury.classe.etablissement.ville,
		'pykol.nom_academie': jury.classe.etablissement.academie.nom_complet,
		'pykol.annee_academique': "{annee_debut}/{annee_fin}".format(
			annee_debut=jury.classe.annee.debut.year,
			annee_fin=jury.classe.annee.fin.year),
		'pykol.ne_accord': "né" if etudiant.sexe == etudiant.SEXE_HOMME \
				else "née",
	}
	mention_globale = jury.mention_set.filter(etudiant=etudiant,
			globale=True).first()
	if mention_globale:
		remplacement['pykol.mention_globale'] = mention_globale.get_mention_display()
		remplacement['pykol.total_ects'] = mention_globale.credits
	else:
		remplacement['pykol.mention_globale'] = "Aucune"
		remplacement['pykol.total_ects'] = "−"


	# On parcourt la nouvelle attestation à la recherche des
	# utilisations des champs utilisations que l'on souhaite
	# substituer.
	for field in attestation.getElementsByType(UserFieldGet)[:]:
		try:
			valeur = remplacement[field.getAttrNS(odf.namespaces.TEXTNS,
				'name')]
		except KeyError:
			continue

		field.parentNode.insertBefore(Span(text=valeur), field)
		field.parentNode.removeChild(field)

	# Suppression des déclarations des champs utilisateurs de
	# l'en-tête du document global.
	for field in attestation.getElementsByType(UserFieldDecl)[:]:
		if field.getAttrNS(odf.namespaces.TEXTNS, 'name') in remplacement:
			field.parentNode.removeChild(field)

	#attestation.rebuild_caches()
	return attestation

def fusion_mentions(etudiant, jury, attestation):
	# Création du tableau des résultats. On trie les mentions par ordre
	# inverse de position car, plus bas, l'ajout au tableau se fait avec
	# insertBefore, avec pour paramètre l'élément immédiatement après
	# l'intitulé du groupe. Par conséquent, les lignes placées en bas
	# doivent être ajoutées en premier.
	mentions = Mention.objects.filter(etudiant=etudiant,
			jury=jury).annotate(position=Min('grille_lignes__position')
			).order_by('-position')
	groupes_mentions = GrilleGroupeLignes.objects.filter(
			lignes__mention__etudiant=etudiant,
			lignes__mention__jury=jury).order_by('position',
					'libelle').values_list('libelle', flat=True).distinct()

	for table_resultats in attestation.getElementsByType(Table):
		if table_resultats.getAttrNS(odf.namespaces.TABLENS, 'name') != 'enseignements':
			continue

		# Insertion de la ligne donnant le titre de la formation
		ligne = TableRow(parent=table_resultats)
		P(text=nom_formation(jury),
			parent=TableCell(parent=ligne, stylename='enseignements.C1',
				numbercolumnsspanned=3),
			stylename='Filière_20_ECTS')
		CoveredTableCell(parent=ligne, numbercolumnsrepeated=2)

		# On prépare les en-têtes des groupes de lignes
		odf_groupes = {}
		for groupe in groupes_mentions:
			# On évite les doublons éventuels sur les libellés (qui
			# pourraient intervenir car le queryset groupes_mentions
			# peut renvoyer le même libellé pour des champs position
			# distincts).
			if groupe in odf_groupes:
				continue

			ligne = TableRow(parent=table_resultats)
			odf_groupes[groupe] = ligne
			P(text=str(groupe),
				parent=TableCell(parent=ligne,
					stylename='enseignements.C1',
					numbercolumnsspanned=3),
				stylename='Groupe_20_ECTS')
			CoveredTableCell(parent=ligne, numbercolumnsrepeated=2)

		# Lorsqu'il existe des mentions présentes dans des groupes et
		# d'autres hors groupes, on prévoit un pour ces dernières un
		# intitulé générique associé au groupe de clé "None".
		if odf_groupes and mentions.filter(grille_lignes__groupe__isnull=True,
				globale=False):
			ligne = TableRow(parent=table_resultats)
			odf_groupes[None] = ligne
			P(text="Autres",
				parent=TableCell(parent=ligne,
					stylename='enseignements.C1',
					numbercolumnsspanned=3),
				stylename='Groupe_20_ECTS')
			CoveredTableCell(parent=ligne, numbercolumnsrepeated=2)

		# On ajoute les mentions au tableau
		mention_globale = None
		for mention in mentions:
			if mention.globale:
				mention_globale = mention
				continue
			if mention.mention is None or \
				Mention.mention == Mention.MENTION_INSUFFISANT:
				continue

			# Si la ligne possède un groupe, elle est positionnée juste
			# après la ligne d'intitulé de ce groupe.
			try:
				groupe = mention.grille_lignes.first().groupe
				cle_groupe = groupe.libelle if groupe is not None else None
				ligne_nextsibling = odf_groupes[cle_groupe].nextSibling
			except Exception as e:
				ligne_nextsibling = None

			ligne = TableRow()
			table_resultats.insertBefore(ligne, ligne_nextsibling)

			P(text=mention.get_libelle_attestation(),
					parent=TableCell(parent=ligne, stylename='enseignements.A1'),
					stylename='Matière_20_ECTS')
			P(text=mention.credits if mention.credits > 0 else "−",
					parent=TableCell(parent=ligne, stylename='enseignements.A1'),
					stylename='Crédits_20_ECTS')
			P(text=(mention.get_mention_display() or "").capitalize(),
					parent=TableCell(parent=ligne, stylename='enseignements.C1'),
					stylename='Mention_20_ECTS')

		# Insertion de la mention globale
		if mention_globale is not None:
			ligne = TableRow(parent=table_resultats)
			P(text="Mention globale",
				parent=TableCell(parent=ligne, stylename='enseignements.A1'),
				stylename='Mention_20_globale_20_ECTS')
			P(text=mention_globale.credits,
				parent=TableCell(parent=ligne, stylename='enseignements.A1'),
				stylename='Crédits_20_ECTS')
			P(text=(mention_globale.get_mention_display() or "").capitalize(),
				parent=TableCell(parent=ligne, stylename='enseignements.C1'),
				stylename='Mention_20_ECTS')

def signature_attestation(attestation, jury):
	"""
	Ajoute la signature du chef d'établissement et le tampon de
	l'établissement sur les attestations passées en argument.

	Si plusieurs attestations sont présentes dans le document, on
	n'ajoute qu'une seule fois les images dans le fichier.

	Cette fonction modifie sur place le paramètre attestation.
	"""
	# Substitution des images (signature du chef et tampon du lycée)
	remplacement_images = {
		'signature_proviseur':
			jury.classe.etablissement.chef_etablissement.signature,
		'tampon_lycee':
			jury.classe.etablissement.tampon_etablissement,
		}
	remplacement_href = {}

	for frame in attestation.getElementsByType(Frame):
		frame_name = frame.getAttrNS(odf.namespaces.DRAWNS, 'name')
		if not remplacement_images.get(frame_name):
			continue

		# Si c'est la première fois que l'on voit cette image, on
		# l'attache au fichier.
		if frame_name not in remplacement_href:
			remplacement_href[frame_name] = attestation.addPicture(
				filename=remplacement_images[frame_name].path)

		for child in frame.childNodes[:]:
			if child.nodeType == child.ELEMENT_NODE:
				child.parentNode.removeChild(child)
		Image(parent=frame, href=remplacement_href[frame_name])

@login_required
def jury_toutes_attestations_resultats(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	etudiants = Etudiant.objects.filter(mention__jury=jury).distinct().order_by(
			'last_name', 'first_name')

	attestations = OpenDocumentText()
	modele_path = os.path.join(settings.BASE_DIR, \
		'pykol/templates/pykol/ects/ects_modele_resultats.odt')
	for etudiant in etudiants:
		modele = odf.opendocument.load(modele_path)
		attestation = fusion_attestation(modele, etudiant, jury)
		fusion_mentions(etudiant, jury, attestation)

		attestations = odtmerge(attestation, attestations)

	signature_attestation(attestations, jury)

	return OdfResponse(attestations, filename="resultats-ects-{classe}-{jury}.odt".format(
		classe=slugify(str(jury.classe)), jury=jury.pk))

@login_required
@permission_required('pykol.direction')
def jury_toutes_attestations_parcours(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	etudiants = Etudiant.objects.filter(mention__jury=jury).distinct().order_by(
			'last_name', 'first_name')

	attestations = OpenDocumentText()
	modele_path = os.path.join(settings.BASE_DIR, \
		'pykol/templates/pykol/ects/ects_modele_attestation_de_parcours.odt')
	for etudiant in etudiants:
		modele = odf.opendocument.load(modele_path)
		attestation = fusion_attestation(modele, etudiant, jury)
		attestations = odtmerge(attestation, attestations)

	signature_attestation(attestations, jury)

	return OdfResponse(attestations, filename="attestation-parcours-ects-{classe}-{jury}.odt".format(
		classe=slugify(str(jury.classe)), jury=jury.pk))

@login_required
@permission_required('pykol.direction')
def jury_attestation_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	# On filtre les étudiants par jury pour ne pas éditer une
	# attestation pour un étudiant qui ne ferait pas partie de ce jury.
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	modele_path = os.path.join(settings.BASE_DIR, \
		'pykol/templates/pykol/ects/ects_modele_resultats.odt')
	attestation = fusion_attestation(odf.opendocument.load(modele_path),
			etudiant, jury)
	fusion_mentions(etudiant, jury, attestation)
	signature_attestation(attestation, jury)

	return OdfResponse(attestation, filename="attestation-ects-{etudiant}-{jury}.odt".format(
		etudiant=slugify(str(etudiant)), jury=jury.pk))
