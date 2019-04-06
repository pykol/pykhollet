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

from collections import OrderedDict

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.forms import modelformset_factory

from pykol.models.ects import Jury, Mention
from pykol.models.base import Etudiant, Enseignement
from pykol.forms.ects import MentionFormSet, JuryForm, JuryDateForm, \
		MentionGlobaleForm, JuryTerminerForm

def jury_list_direction(request):
	"""
	Affichage de tous les jurys par la direction.
	"""
	jury_list = Jury.objects.all().annotate(
			mentions_reste=Count('mention',
				filter=Q(mention__mention__isnull=True))
		).order_by('date')

	jury_creer_form = JuryForm()

	return render(request, 'pykol/ects/jury_list_direction.html',
		context={
			'jury_list': jury_list,
			'jury_creer_form': jury_creer_form,
		})

def jury_list_professeur(request):
	"""
	Affichage des jurys auxquels participe un professeur.
	"""
	jury_list = Jury.objects.filter(
			mention__enseignement__professeurs=request.user
		).annotate(
			mentions_reste=Count('mention',
				filter=Q(
					mention__mention__isnull=True,
				)
			)
		).order_by('date')

	return render(request, 'pykol/ects/jury_list_professeur.html',
		context={
			'jury_list': jury_list,
		})

def jury_list_etudiant(request):
	"""
	Affichage des jurys qui ont évalué l'étudiant.
	"""
	pass

@login_required
def jury_list(request):
	"""
	Affichage de la liste de tous les jurys, adaptée en fonction du
	profil de l'utilisateur connecté.

	La direction peut consulter tous les jurys, les professeurs peuvent
	consulter les jurys dont ils sont membres et les étudiants peuvent
	consulter les jurys dans lesquels des crédits leur ont été
	attribués.
	"""
	if request.user.has_perm('pykol.direction'):
		return jury_list_direction(request)
	elif hasattr(request.user, 'professeur'):
		return jury_list_professeur(request)
	elif hasattr(request.user, 'etudiant'):
		return jury_list_etudiant(request)
	else:
		raise PermissionDenied

def jury_detail_direction(request, jury):
	if request.method == 'POST' and 'submit_jurymodif' in request.POST:
		form = JuryDateForm(request.POST, instance=jury, prefix='jurymodif')
		if form.is_valid():
			form.save()
			return redirec('ects_jury_detail', jury.pk)
	else:
		form = JuryDateForm(instance=jury, prefix='jurymodif')

	# Liste des étudiants de ce jury avec les décomptes de crédits ECTS
	etudiants = Etudiant.objects.filter(
		mention__jury=jury,
		mention__globale=False,
	).annotate(
		credits_prevus=Coalesce(Sum('mention__credits'), 0),
		credits_attribues=Coalesce(Sum('mention__credits',
			filter=~Q(mention__mention=Mention.MENTION_INSUFFISANT)
				& Q(mention__mention__isnull=False)
			), 0),
		credits_refuses=Coalesce(Sum('mention__credits',
			filter=Q(mention__mention=Mention.MENTION_INSUFFISANT)), 0)
	).order_by('last_name', 'first_name')

	# On convertit tout de suite la requête sur les étudiants en liste
	# afin d'ajouter les formulaires pour donner les mentions globales.
	etudiants = list(etudiants)
	mention_initial = []
	mention_extra = 0
	# Dictionnaire qui à chaque étudiant de la liste etudiants, associe
	# un entier j qui désigne une position dans mention_initial (donc
	# plus tard, une position dans les formulaires de mention_formset).
	# Ceci permet, une fois le formulaire mention_formset construit,
	# d'ajouter facilement le champ mention_globale_form à chaque
	# étudiant.
	map_form_etudiant = {}
	for etudiant in etudiants:
		# TODO veut-on vérifier que les mentions facultatives ont été
		# remplies ?
		try:
			mention = Mention.objects.get(globale=True, jury=jury,
				etudiant=etudiant)
			mention_initial.append({
					'etudiant': etudiant.pk,
					'id': mention.pk,
					'mention': mention.mention,
					'jury': jury.pk,
					'credits': mention.credits,
				})
			map_form_etudiant[etudiant] = len(mention_initial) - 1
		except Mention.DoesNotExist:
			if etudiant.credits_prevus == etudiant.credits_attribues:
				mention_initial.append({
					'etudiant': etudiant.pk,
					'jury': jury.pk,
					'credits': etudiant.credits_attribues,
				})
				map_form_etudiant[etudiant] = len(mention_initial) - 1
				mention_extra += 1
	MentionGlobaleFormSet = modelformset_factory(Mention,
		fields=MentionGlobaleForm.Meta.fields, can_delete=False,
		extra=mention_extra, form=MentionGlobaleForm)

	if request.method == 'POST' and 'submit_mentions' in request.POST:
		mention_formset = MentionGlobaleFormSet(request.POST,
				initial=mention_initial,
				prefix='mentions',
				queryset=Mention.objects.filter(jury=jury, globale=True))
		if mention_formset.is_valid():
			mention_formset.save()
			return redirect('ects_jury_detail', jury.pk)
	else:
		mention_formset = MentionGlobaleFormSet(
				initial=mention_initial,
				prefix='mentions',
				queryset=Mention.objects.filter(jury=jury, globale=True))

	# On attache chaque formulaire du mention_formset à son étudiant
	for etudiant, pos_form in map_form_etudiant.items():
		etudiant.mention_globale_form = mention_formset.forms[pos_form]

	return render(request, 'pykol/ects/jury_detail_direction.html',
		context={
			'form': form,
			'jury': jury,
			'etudiants': etudiants,
			'mention_formset': mention_formset,
		})

def jury_detail_professeur(request, jury):
	mention_qs = Mention.objects.filter(jury=jury,
			enseignement__professeurs=request.user)

	if request.method == 'POST' and jury.etat != Jury.ETAT_TERMINE:
		formset = MentionFormSet(request.POST, instance=jury,
				queryset=mention_qs)
		if formset.is_valid():
			formset.save()
			return redirect('ects_jury_detail', jury.pk)
	else:
		formset = MentionFormSet(instance=jury,
			queryset=mention_qs)

	# On réarrange le formset pour présenter un étudiant par ligne, une
	# matière par colonne.
	enseignements = set()
	for mention in mention_qs:
		enseignements.add((mention.enseignement,
			mention.grille_lignes.first()))
	enseignements = sorted(enseignements,
		key=lambda x: (x[0].periode, -x[1].credits, x[0].pk))

	etudiants = Etudiant.objects.filter(
		mention__in=mention_qs).order_by('last_name', 'first_name')

	formsettab = OrderedDict()
	for etudiant in etudiants:
		formsettab[etudiant] = OrderedDict()
		for enseignement in enseignements:
			formsettab[etudiant][enseignement] = None
	for form in formset:
		formsettab[form.instance.etudiant][(form.instance.enseignement,
			form.instance.grille_lignes.first())] = form
	formsettab.management_form = formset.management_form
	formsettab.errors = formset.errors

	return render(request, 'pykol/ects/jury_detail_professeur.html',
		context={
			'formsettab': formsettab,
			'jury': jury,
			'enseignements': enseignements,
			'etudiants': etudiants,
		})

def jury_detail_etudiant(request, jury):
	pass

@login_required
def jury_detail(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	if request.user.has_perm('pykol.direction'):
		return jury_detail_direction(request, jury)
	elif hasattr(request.user, 'professeur'):
		return jury_detail_professeur(request, jury)
	elif hasattr(request.user, 'etudiant'):
		return jury_detail_etudiant(request, jury)
	else:
		raise PermissionDenied

@login_required
def jury_creer(request):
	if request.method == 'POST':
		form = JuryForm(request.POST)
		if form.is_valid():
			Jury.objects.create_from_classe(classe=form.cleaned_data['classe'],
				date=form.cleaned_data['date'],
				periode=form.cleaned_data['periode'])
			return redirect('ects_jury_list')
	else:
		form = JuryForm()

	return render(request, 'pykol/ects/jury_creer.html',
		context={'jury_creer_form': form})

@login_required
def jury_supprimer(request, pk):
	jury = get_object_or_404(Jury, pk=pk)
	pass

@login_required
def jury_detail_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	# On filtre les étudiants par jury pour ne pas éditer une
	# attestation pour un étudiant qui ne ferait pas partie de ce jury.
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	mentions = etudiant.mention_set.filter(jury=jury, globale=False
		)

	mention_globale = etudiant.mention_set.filter(jury=jury,
			globale=True).first()

	return render(request, 'pykol/ects/jury_detail_etudiant.html',
			context={
				'jury': jury,
				'etudiant': etudiant,
				'mentions': mentions,
				'mention_globale': mention_globale,
			})