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

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from django.utils.text import slugify

import odf.opendocument
from odf.text import UserFieldDecl, UserFieldGet, Span, P
from odf.table import Table, TableCell, TableRow, CoveredTableCell
from odf.draw import Frame, Image
import odf.namespaces

from pykol.models.ects import Jury, Mention, GrilleGroupeLignes
from pykol.models.base import Etudiant, Enseignement

def fusion_attestation(etudiant, jury):
	"""
	Charge le modèle OpenDocument d'attestation de résultats et remplace
	les champs utilisateurs par les données de l'étudiant. Cette
	fonction renvoie le document OpenDocument modifié.
	"""
	modele_path = os.path.join(settings.BASE_DIR, \
			'pykol/data/ects_modele_resultats.odt')
	doc = odf.opendocument.load(modele_path)
	remplacement = {
		'pykol.date_naissance_etudiant': etudiant.birth_date.strftime("%d/%m/%Y"),
		'pykol.ine_etudiant': etudiant.ine,
		'pykol.nom_formation': jury.classe.mef.libelle_ects,
		'pykol.domaines_etude': jury.classe.mef.domaines_etude,
		'pykol.nom_etudiant': str(etudiant),
		'pykol.date_attestation': jury.date.strftime("%d/%m/%Y"),
		'pykol.nom_signataire': jury.classe.etablissement.chef_etablissement.name_civilite(),
		'pykol.nom_lycee': jury.classe.etablissement.appellation,
		'pykol.statut_lycee': jury.classe.etablissement.get_nature_uai_display(),
		'pykol.ville_lycee': jury.classe.etablissement.ville,
	}

	# Remplacement des champs utilisateurs par leurs valeurs.
	for field in doc.getElementsByType(UserFieldGet):
		try:
			valeur = remplacement[field.getAttrNS(odf.namespaces.TEXTNS,
				'name')]
		except KeyError:
			continue

		field.parentNode.insertBefore(Span(text=valeur), field)
		field.parentNode.removeChild(field)

	# Suppression des déclarations des champs utilisateurs de l'en-tête.
	for field in doc.getElementsByType(UserFieldDecl):
		if field.getAttrNS(odf.namespaces.TEXTNS, 'name') in remplacement:
			field.parentNode.removeChild(field)


	# Substitution des images (signature du chef et tampon du lycée)
	remplacement_images = {
		'signature_proviseur':
			jury.classe.etablissement.chef_etablissement.signature,
		'tampon_lycee':
			jury.classe.etablissement.tampon_etablissement,
		}
	remplacement_href = {}

	for frame in doc.getElementsByType(Frame):
		frame_name = frame.getAttrNS(odf.namespaces.DRAWNS, 'name')
		if not remplacement_images.get(frame_name):
			continue

		# Si c'est la première fois que l'on voit cette image, on
		# l'attache au fichier.
		if frame_name not in remplacement_href:
			remplacement_href[frame_name] = doc.addPicture(
				filename="Pictures/{name}{ext}".format(
					name=frame_name,
					ext=os.path.splitext(remplacement_images[frame_name].name)[1]),
				content=remplacement_images[frame_name].read())

		for child in frame.childNodes:
			if child.nodeType == child.ELEMENT_NODE:
				child.parentNode.removeChild(child)
		Image(parent=frame, href=remplacement_href[frame_name])

	# Un bug de odfpy fait que le cache d'éléments n'est plus à jour à
	# case de l'ajout des objets Image dans la boucle précédente. On
	# vide ce cache de force sinon l'appel suivant de getElementsByType
	# échoue et renvoie une liste vide.
	doc.clear_caches()

	# Création du tableau des résultats. On trie les mentions par ordre
	# inverse de position car, plus bas, l'ajout au tableau se fait avec
	# insertBefore, avec pour paramètre l'élément immédiatement après
	# l'intitulé du groupe. Par conséquent, les lignes placées en bas
	# doivent être ajoutées en premier.
	mentions = Mention.objects.filter(etudiant=etudiant,
			jury=jury).order_by('-grille_lignes__position').distinct()
	groupes_mentions = GrilleGroupeLignes.objects.filter(
			lignes__mention__etudiant=etudiant,
			lignes__mention__jury=jury).order_by('position',
					'libelle').values_list('libelle', flat=True).distinct()

	for table_resultats in doc.getElementsByType(Table):
		if table_resultats.getAttrNS(odf.namespaces.TABLENS, 'name') != 'enseignements':
			continue

		# Insertion de la ligne donnant le titre de la formation
		ligne = TableRow(parent=table_resultats)
		P(text=jury.classe.mef.libelle_ects,
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
				ligne_nextsibling = \
					odf_groupes[mention.grille_lignes.first().groupe.libelle].nextSibling
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
				stylename='Matière_20_ECTS')
			P(text=mention_globale.credits,
				parent=TableCell(parent=ligne, stylename='enseignements.A1'),
				stylename='Crédits_20_ECTS')
			P(text=(mention_globale.get_mention_display() or "").capitalize(),
				parent=TableCell(parent=ligne, stylename='enseignements.C1'),
				stylename='Mention_20_ECTS')

	return doc

@login_required
def jury_toutes_attestations(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	pass

@login_required
#@permission_required('pykol.direction')
def jury_attestation_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	# On filtre les étudiants par jury pour ne pas éditer une
	# attestation pour un étudiant qui ne ferait pas partie de ce jury.
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	doc = fusion_attestation(etudiant, jury)

	response = HttpResponse(content_type=doc.getMediaType())
	response['Content-Disposition'] = \
		'attachment; filename="attestation-ects-{etudiant}-{jury}.odt"'.format(
				etudiant=slugify(str(etudiant)), jury=jury.pk)
	doc.write(response)

	return response
