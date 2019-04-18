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
import copy

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

def fusion_attestation(modele, etudiant, jury):
	"""
	Remplace dans un modèle OpenDocument d'attestation de résultats
	les champs utilisateurs par les données de l'étudiant. Cette
	fonction renvoie le document OpenDocument modifié. Le modèle est
	copié, donc n'est pas modifié par l'appel.
	"""
	attestation = copy.deepcopy(modele)

	remplacement = {
		'pykol.date_naissance_etudiant': etudiant.birth_date.strftime("%d/%m/%Y"),
		'pykol.ine_etudiant': etudiant.ine,
		'pykol.nom_formation': "{libelle} − {niveau}".format(
			libelle=jury.classe.mef.libelle_ects,
			niveau=jury.classe.get_niveau_display()),
		'pykol.domaines_etude': jury.classe.mef.domaines_etude,
		'pykol.nom_etudiant': str(etudiant),
		'pykol.date_attestation': jury.date.strftime("%d/%m/%Y"),
		'pykol.nom_signataire': jury.classe.etablissement.chef_etablissement.name_civilite(),
		'pykol.nom_lycee': jury.classe.etablissement.appellation,
		'pykol.statut_lycee': jury.classe.etablissement.get_nature_uai_display(),
		'pykol.ville_lycee': jury.classe.etablissement.ville,
	}

	# On parcourt la nouvelle attestation à la recherche des
	# utilisations des champs utilisations que l'on souhaite
	# substituer.
	for field in attestation.getElementsByType(UserFieldGet):
		try:
			valeur = remplacement[field.getAttrNS(odf.namespaces.TEXTNS,
				'name')]
		except KeyError:
			continue

		field.parentNode.insertBefore(Span(text=valeur), field)
		field.parentNode.removeChild(field)

	# Suppression des déclarations des champs utilisateurs de
	# l'en-tête du document global.
	for field in attestation.getElementsByType(UserFieldDecl):
		if field.getAttrNS(odf.namespaces.TEXTNS, 'name') in remplacement:
			field.parentNode.removeChild(field)

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

	for table_resultats in attestation.getElementsByType(Table):
		if table_resultats.getAttrNS(odf.namespaces.TABLENS, 'name') != 'enseignements':
			continue

		# Insertion de la ligne donnant le titre de la formation
		ligne = TableRow(parent=table_resultats)
		P(text=remplacement['pykol.nom_formation'],
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

	return attestation

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
	attestation.clear_caches()

@login_required
def jury_toutes_attestations(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	etudiants = Etudiant.objects.filter(mention__jury=jury).distinct()

	attestations = None
	modele_path = os.path.join(settings.BASE_DIR, \
		'pykol/data/ects_modele_resultats.odt')
	modele = odf.opendocument.load(modele_path)
	for etudiant in etudiants:
		attestation = fusion_attestation(modele, etudiant, jury)
		if attestations is None:
			attestations = attestation
		else:
			for child in attestation.body.childNodes:
				attestations.body.appendChild(child)

	# odfpy ne met pas à jour correctement ses caches en cas d'appel à
	# appendChild (les fils ne sont pas rattachés au document). On force
	# la mise à jour.
	attestations.clear_caches()

	signature_attestation(attestations, jury)

	response = HttpResponse(content_type=attestations.getMediaType())
	response['Content-Disposition'] = \
		'attachment; filename="attestation-ects-{classe}-{jury}.odt"'.format(
				classe=slugify(str(jury.classe)), jury=jury.pk)
	attestations.write(response)

	return response

@login_required
#@permission_required('pykol.direction')
def jury_attestation_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	# On filtre les étudiants par jury pour ne pas éditer une
	# attestation pour un étudiant qui ne ferait pas partie de ce jury.
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	modele_path = os.path.join(settings.BASE_DIR, \
		'pykol/data/ects_modele_resultats.odt')
	attestation = fusion_attestation(odf.opendocument.load(modele_path),
			etudiant, jury)
	signature_attestation(attestation, jury)

	response = HttpResponse(content_type=attestation.getMediaType())
	response['Content-Disposition'] = \
		'attachment; filename="attestation-ects-{etudiant}-{jury}.odt"'.format(
				etudiant=slugify(str(etudiant)), jury=jury.pk)
	attestation.write(response)

	return response
