# -*- coding: utf-8

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

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, \
		UserPassesTestMixin, AccessMixin
from django.utils import timezone
from django.db.models import Func, F
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from pykol.models.base import Etudiant, Annee, JetonAcces
from pykol.models.colles import Colle
from pykol.forms.colles import ColleNoteFormSet, ColleModifierForm
from pykol.lib.auth import colle_user_permissions
from pykol.lib.shortcuts import redirect_next

"""
Vues de gestion des colles destinées aux colleurs.

Ces vues permettent de déclarer les notes de colles, de déplacer des
colles ou de les annuler (ce qui ne les supprime pas de la base).

Elles ne permettent ni de créer des colles, ni de supprimer des colles :
ces tâches relèvent de la gestion du colloscope, et se trouvent dans le
fichier colloscope.py
"""

def colle_visible_par(user, colle):
	"""Renvoie True si et seulement si l'utilisateur a le droit de
	consulter les détails de la colle."""
	return user.has_perm('pykol.view_colle', colle)

class ColleVisibleMixin(generic.detail.SingleObjectMixin,
		UserPassesTestMixin):
	"""Application du test colle_visible_par à une vue sur la colle"""
	model = Colle
	def test_func(self):
		return colle_visible_par(self.request.user, self.get_object())

class ColleDetailView(LoginRequiredMixin, ColleVisibleMixin, \
		generic.DetailView):
	"""
	Affichage de tous les détails d'une colle
	"""
	template_name = 'pykol/colles/colle_detail.html'
	model = Colle

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		colle = self.get_object()

		context['anciens_details'] = \
				colle.colledetails_set.filter(actif=False)

		context['perm_colle'] = \
				colle_user_permissions(self.request.user, colle)

		if self.request.user.has_perm('pykol.change_colle', colle):
			context['tous_etudiants'] = 'tous_etudiants' in self.request.GET
			if context['tous_etudiants']:
				etudiants_qs = Etudiant.objects.filter(classe__annee=Annee.objects.get_actuelle())
			else:
				etudiants_qs = None
			context['deplacer_form'] = ColleModifierForm(colle=colle,
					etudiants=etudiants_qs)

		return context

colle_detail = ColleDetailView.as_view()

@login_required
def colle_declarer(request, pk):
	"""
	Vue qui permet de déclarer les notes pour une colle déjà existante
	dans la base de données, identifiée par sa clé pk.
	"""
	colle = get_object_or_404(Colle, pk=pk)

	# Seul le colleur peut noter sa colle
	if not request.user.has_perm('pykol.add_collenote', colle):
		raise PermissionDenied

	# Les colles sous la forme de TD n'ont pas de notes, il suffit de
	# confirmer qu'elles ont été réalisées (et avec une requête POST,
	# obligatoire pour modifier la base de données).
	if colle.mode == Colle.MODE_TD:
		if request.method == 'POST':
			colle.effectuer()
		return redirect_next('colle_detail', colle.pk, request=request)

	# Les colles sans élèves ne peuvent pas être notées.
	if len(colle.details.eleves.all()) == 0:
		return render(request, 'pykol/colles/noter_sans_eleves.html',
			context={'colle': colle})

	# On peuple le formulaire avec les élèves qui n'ont pas encore été
	# notés.
	eleves_sans_note = colle.details.eleves.difference(
		Etudiant.objects.filter(collenote__colle=colle))
	initial = []
	for eleve in eleves_sans_note:
		initial.append({'eleve' : eleve})

	if request.method == 'POST':
		form = ColleNoteFormSet(request.POST, instance=colle,
				initial=initial)
		form.extra = len(initial)
		if form.is_valid():
			form.save()

			# Quand tous les élèves sont notés, on indique que la colle
			# est notée.
			eleves_sans_note = colle.details.eleves.difference(
				Etudiant.objects.filter(collenote__colle=colle))
			if not eleves_sans_note and colle.etat != Colle.ETAT_RELEVEE:
				colle.effectuer()

			return redirect_next('colle_detail', colle.pk,
					request=request)
	else:
		form = ColleNoteFormSet(instance=colle, initial=initial)
		form.extra = len(initial)

	context = {'colle': colle, 'form': form}

	next_url = request.POST.get('next', request.GET.get('next'))
	if next_url:
		if url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
			context['next_url'] = next_url

	return render(request, 'pykol/colles/noter.html', context)

@login_required
def colle_deplacer(request, pk):
	"""
	Vue qui permet de modifier les détails d'une colle (date, lieu,
	etc.)
	"""
	colle = get_object_or_404(Colle, pk=pk)

	if not request.user.has_perm('pykol.change_colle', colle):
		raise PermissionDenied

	if request.method == 'POST':
		form = ColleModifierForm(request.POST, colle=colle, etudiants=
				Etudiant.objects.filter(classe__annee=Annee.objects.get_actuelle()))
		if form.is_valid():
			etudiants = form.cleaned_data.get('etudiants').all()
			if not etudiants:
				etudiants = []

			if form.cleaned_data.get('mode') is not None:
				colle.mode = form.cleaned_data.get('mode')
				colle.save()

			colle.ajout_details(
				horaire=form.cleaned_data.get('horaire'),
				salle=form.cleaned_data.get('salle'),
				colleur=form.cleaned_data.get('colleur'),
				etudiants=etudiants,
			)
			return redirect('colle_detail', colle.pk)
	else:
		form = ColleModifierForm(colle=colle)

	return render(request, 'pykol/colles/deplacer.html', context={
		'colle': colle, 'form': form,})

@login_required
@require_POST
def colle_annuler(request, pk):
	"""
	Annulation d'une colle par le colleur
	"""
	colle = get_object_or_404(Colle, pk=pk)

	# On ne change pas les colles des copains
	if not request.user.has_perm('pykol.change_colle', colle):
		raise PermissionDenied

	if colle.etat == Colle.ETAT_PREVUE:
		colle.annuler()
		messages.success(request, "La colle a bien été annulée")
	else:
		messages.error(request, "On ne peut pas annuler une colle déjà notée ou déjà relevée")

	return redirect('colle_list')

class ProfesseurColleListView(LoginRequiredMixin, generic.ListView):
	"""
	Affichage des colles pour le colleur actuellement connecté
	"""
	template_name = 'pykol/colles/colle_list_passe.html'

	def get_queryset(self):
		return Colle.objects.filter(
			colledetails__colleur=self.request.user,
			colledetails__actif=True).order_by('colledetails__horaire').annotate(
				a_noter=Func(F('colledetails__horaire'),
					timezone.localtime(), arity=2, arg_joiner='<',
					function='')
				)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['next_url'] = reverse('colle_list')

		# Pour la séparation colles passées et futures, on laisse quand
		# même un délai de grâce de 3 jours avant de les reléguer en fin
		# de page.
		limite_futur = timezone.localtime() - timedelta(days=3)
		colle_list = self.get_queryset()
		context['colles_futures'] = colle_list.filter(colledetails__actif=True, colledetails__horaire__gte=limite_futur)
		context['colles_passees'] = colle_list.filter(colledetails__actif=True, colledetails__horaire__lt=limite_futur)

		# Ajout d'un lien vers la version iCalendar du planning des
		# colles. Si nécessaire, on crée automatiquement le jeton
		# d'accès.
		try:
			ical_jeton = JetonAcces.objects.filter(owner=self.request.user,
				scope='colles_icalendar')[0]
		except IndexError:
			ical_jeton = JetonAcces(owner=self.request.user,
				scope='colles_icalendar')
			ical_jeton.save()
		context['ical_url'] = reverse('colle_calendrier',
				kwargs={'uuid': ical_jeton.uuid})

		return context

class EtudiantColleListView(LoginRequiredMixin, generic.ListView):
	"""
	Affichage des colles pour le colleur actuellement connecté
	"""
	template_name = 'pykol/colles/colle_list_passe_etudiant.html'

	def get_queryset(self):
		return Colle.objects.filter(
			colledetails__eleves=self.request.user,
			colledetails__actif=True).order_by('colledetails__horaire')

	def get_limite_futur(self):
		return timezone.localtime() - timedelta(days=3)

	def get_queryset_futures(self):
		return self.get_queryset().filter(colledetails__actif=True,
				colledetails__horaire__gte=self.get_limite_futur())

	def get_queryset_passees(self):
		return self.get_queryset().filter(colledetails__actif=True,
				colledetails__horaire__lt=self.get_limite_futur())

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		# Pour la séparation colles passées et futures, on laisse quand
		# même un délai de grâce de 3 jours avant de les reléguer en fin
		# de page.
		context['colles_futures'] = self.get_queryset_futures()
		context['colles_passees'] = self.get_queryset_passees()

		# Ajout d'un lien vers la version iCalendar du planning des
		# colles. Si nécessaire, on crée automatiquement le jeton
		# d'accès.
		try:
			ical_jeton = JetonAcces.objects.filter(owner=self.request.user,
				scope='colles_icalendar')[0]
		except IndexError:
			ical_jeton = JetonAcces(owner=self.request.user,
				scope='colles_icalendar')
			ical_jeton.save()
		context['ical_url'] = reverse('colle_calendrier',
				kwargs={'uuid': ical_jeton.uuid})

		return context

class ColleListView(AccessMixin, generic.View):
	def dispatch(self, request, *args, **kwargs):
		if request.user.is_authenticated:
			if hasattr(request.user, 'professeur'):
				return ProfesseurColleListView.as_view()(request, *args, **kwargs)
			elif hasattr(request.user, 'etudiant'):
				return EtudiantColleListView.as_view()(request, *args, **kwargs)

		return self.handle_no_permission()

colle_list = ColleListView.as_view()

class ColleANoterListView(ProfesseurColleListView):
	"""
	Affichage des colles en attente de notation pour le colleur
	"""
	template_name = 'pykol/colles/colle_list.html'

	def get_queryset(self):
		return super().get_queryset().filter(etat=Colle.ETAT_PREVUE,
				colledetails__horaire__lte=timezone.localtime(),
				colledetails__actif=True,
				classe__annee=Annee.objects.get_actuelle())

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['next_url'] = reverse('colles_a_noter')
		return context

colle_a_noter_list = ColleANoterListView.as_view()
