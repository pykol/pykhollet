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

from django.db.models import Count, Q, Sum, F
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, \
		permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.forms import modelformset_factory
from django.views.decorators.http import require_POST

from pykol.models.ects import Jury, Mention
from pykol.models.base import Etudiant, Enseignement, Annee
from pykol.forms.ects import MentionFormSet, JuryForm, JuryDateForm, \
		MentionGlobaleForm, JuryTerminerForm
from pykol.lib.shortcuts import redirect_next

def jury_list_direction(request):
	"""
	Affichage de tous les jurys par la direction.
	"""
	jury_list = Jury.objects.all().annotate(
			mentions_reste=Count('mention',
				filter=Q(mention__mention__isnull=True)),
			annee=F('classe__annee'),
		).order_by('-annee', 'date')

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
			mention__enseignement__professeurs=request.user,
			classe__annee=Annee.objects.get_actuelle(),
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
			return redirect('ects_jury_detail', jury.pk)
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

	# On convertit tout de suite la requête sur les étudiants en
	# dictionnaire afin d'ajouter les formulaires pour donner les
	# mentions globales.
	etudiants = OrderedDict([(e.pk, e) for e in etudiants])
	mention_initial = []

	# On récupère d'abord les mentions globales déjà existantes dans la
	# base de données.
	mentions_globales = jury.mention_set.filter(globale=True)
	for mention in mentions_globales:
		etudiants[mention.etudiant.pk].mention_globale = mention

	# On prépare le formulaire pour les mentions globales que l'on peut
	# créer (lorsque tous les crédits prévus sont effectivement
	# accordés).
	mention_extra = 0
	for etudiant in etudiants.values():
		# TODO veut-on vérifier que les mentions facultatives ont été
		# remplies ?
		if hasattr(etudiant, 'mention_globale'):
			continue
		if etudiant.credits_prevus == etudiant.credits_attribues:
			mention_initial.append({
				'etudiant': etudiant.pk,
				'jury': jury.pk,
				'credits': etudiant.credits_attribues,
			})
			mention_extra += 1

	MentionGlobaleFormSet = modelformset_factory(Mention,
		fields=MentionGlobaleForm.Meta.fields, can_delete=False,
		extra=mention_extra, form=MentionGlobaleForm)

	if request.method == 'POST' and 'submit_mentions' in request.POST:
		mention_formset = MentionGlobaleFormSet(request.POST,
				initial=mention_initial,
				prefix='mentions',
				queryset=mentions_globales)
		if mention_formset.is_valid():
			mention_formset.save()
			return redirect('ects_jury_detail', jury.pk)
	else:
		mention_formset = MentionGlobaleFormSet(
				initial=mention_initial,
				prefix='mentions',
				queryset=mentions_globales)

	# On attache chaque formulaire du mention_formset à son étudiant
	for mention_form in mention_formset:
		etudiants[mention_form['etudiant'].initial].mention_globale_form = mention_form

	return render(request, 'pykol/ects/jury_detail_direction.html',
		context={
			'form': form,
			'jury': jury,
			'etudiants': etudiants.values(),
			'mention_formset': mention_formset,
		})

def jury_saisie_mentions(request, jury, mention_qs):
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
		key=lambda x: (x[0].periode,
			-x[1].credits if x[1] is not None else 0,
			x[0].pk))

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
	pass

def jury_detail_professeur(request, jury):
	mention_qs = Mention.objects.filter(jury=jury,
			enseignement__professeurs=request.user).distinct()
	return jury_saisie_mentions(request, jury, mention_qs)

@permission_required('pykol.direction')
def jury_mentions_orphelines(request, pk):
	"""
	Saisie des mentions par la direction pour les enseignements qui
	n'ont aucun professeur attribué.
	"""
	jury = get_object_or_404(Jury, pk=pk)
	mention_qs = Mention.objects.filter(jury=jury,
			enseignement__professeurs__isnull=True,
			enseignement__isnull=False)
	return jury_saisie_mentions(request, jury, mention_qs)

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

@require_POST
@login_required
@permission_required('pykol.direction')
def jury_supprimer(request, pk):
	"""
	Suppression d'un jury par la direction. Si des mentions ont déjà été
	saisies par les professeurs, cette vue demande une confirmation
	avant de supprimer le jury.
	"""
	jury = get_object_or_404(Jury, pk=pk)
	if 'confirmer' in request.POST or \
		not jury.mention_set.filter(mention__isnull=False):
			jury.delete()
			return redirect_next('ects_jury_list', request=request)
	else:
		return render(request,
			'pykol/ects/jury_confirmer_suppression.html',
			context={
				'jury': jury,
				'nombre_mentions': len(jury.mention_set.filter(mention__isnull=False)),
			})

@login_required
def jury_detail_etudiant(request, pk, etu_pk):
	jury = get_object_or_404(Jury, pk=pk)
	# On filtre les étudiants par jury pour ne pas éditer une
	# attestation pour un étudiant qui ne ferait pas partie de ce jury.
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	mentions = etudiant.mention_set.filter(jury=jury, globale=False)

	mention_globale = etudiant.mention_set.filter(jury=jury,
			globale=True).first()

	credits = mentions.aggregate(
		prevus=Coalesce(Sum('credits'), 0),
		attribues=Coalesce(Sum('credits',
			filter=~Q(mention=Mention.MENTION_INSUFFISANT)
				& Q(mention__isnull=False)
			), 0),
		refuses=Coalesce(Sum('credits',
			filter=Q(mention=Mention.MENTION_INSUFFISANT)), 0)
	)

	if request.user.has_perm('pykol.direction') and (
		mention_globale is not None or credits['prevus'] == credits['attribues']):
		if mention_globale is None:
			form_kwargs = {'initial': {
				'jury': jury.pk,
				'etudiant': etudiant.pk,
				'credits': credits['attribues'],
				}
			}
		else:
			form_kwargs = {'instance': mention_globale}

		if request.method == 'POST':
			mention_globale_form = MentionGlobaleForm(request.POST,
					**form_kwargs)

			if mention_globale_form.is_valid():
				mention_globale_form.save()
				if 'save_next' in request.POST:
					etudiants_jury = Etudiant.objects.filter(
							mention__jury=jury,
					).distinct().order_by('last_name', 'first_name').values_list('pk', flat=True)
					next_pk = None
					prev_pk = None
					for next_pk in etudiants_jury:
						if prev_pk == etu_pk:
							break
						prev_pk = next_pk
					else:
						return redirect('ects_jury_detail', pk)

					if next_pk is not None:
						return redirect('ects_jury_detail_etudiant', pk, next_pk)

				return redirect('ects_jury_detail_etudiant', pk, etu_pk)
		else:
			mention_globale_form = MentionGlobaleForm(**form_kwargs)
	else:
		mention_globale_form = None

	return render(request, 'pykol/ects/jury_detail_etudiant.html',
			context={
				'jury': jury,
				'etudiant': etudiant,
				'mentions': mentions.order_by('-credits'),
				'mention_globale': mention_globale,
				'mention_globale_form': mention_globale_form,
			})

@require_POST
@permission_required('pykol.direction')
def jury_retirer_etudiant(request, pk, etu_pk):
	"""
	Suppression de toutes les mentions prévues pour un étudiant dans le
	jury donné.
	"""
	jury = get_object_or_404(Jury, pk=pk)
	etudiant = get_object_or_404(Etudiant, pk=etu_pk,
			classe__jury=jury)

	mentions = etudiant.mention_set.filter(jury=jury)

	if 'confirmer' in request.POST or not mentions:
			mentions.delete()
			return redirect_next('ects_jury_detail', jury.pk, request=request)
	else:
		return render(request,
			'pykol/ects/jury_confirmer_suppression_etudiant.html',
			context={
				'jury': jury,
				'etudiant': etudiant,
				'nombre_mentions': len(mentions.filter(mention__isnull=False)),
			})
