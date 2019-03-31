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

import odf.opendocument
from odf.text import UserFieldDecl, UserFieldGet, Span
import odf.namespaces

from pykol.models.ects import Jury, Mention
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
		'pykol.date_naissance_etudiant':
			etudiant.date_naissance.strftime("%d/%m/%Y"),
		'pykol.ine_etudiant': etudiant.ine,
		'pykol.nom_formation': jury.classe.mef.libelle_ects,
		'pykol.domaines_etude': jury.classe.mef.domaines_etude,
		'pykol.nom_etudiant': str(etudiant),
		'pykol.date_attestation': jury.date.strftime("%d/%m/%Y"),
		'pykol.nom_signataire':
			jury.classe.etablissement.chef_etablissement.name_civilite(),
		'pykol.nom_lycee': jury.classe.etablissement.appellation,
		'pykol.statut_lycee': jury.classe.etablissement.get_nature_uai_display(),
		'pykol.ville_lycee': ...,
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

	# Création du tableau des résultats.
	mentions = Mention.objects.filter(etudiant=etudiant,
			jury=jury).order_by('ligne__position')
	for table_resultats in doc.getElementsByType(Table):
		if table_resultats.getAttrNS(odf.namespaces.TABLENS, 'name') != 'enseignements':
			continue

		mention_globale = None
		for mention in mentions:
			if mention.globale:
				mention_globale = mention_globale
				continue
			ligne = TableRow()
			P(text=mention.ligne, parent=TableCell(parent=ligne))
			P(text=mention.credits, parent=TableCell(parent=ligne))
			P(text=mention.get_mention_display(), parent=TableCell(parent=ligne))

		# TODO insérer la mention globale ?

	return doc

@login_required
def jury_toutes_attestations(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	pass

@login_required
def jury_attestation_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	etudiant = get_object_or_404(Etudiant, pk=etu_pk)
	doc = fusion_attestation(etudiant, jury)
	response = HttpResponse(content_type=doc.getMediaType())
	response['Content-Disposition'] = \
		'attachment; filename="attestation-ects-{etudiant}-{jury}.odt"'.format(
				etudiant=slugify(str(etudiant)), jury=jury.pk)
	doc.write(response)
	return response
