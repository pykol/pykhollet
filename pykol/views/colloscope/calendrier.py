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

from django.views.generic import DetailView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.shortcuts import get_object_or_404
from django.urls import reverse

from pykol.models.base import Enseignement, Professeur
from pykol.models.colles import Colle
from pykol.forms.colloscope import CalendrierColleurFormset

class CalendrierMatiereView(DetailView):
	"""
	Accès au calendrier de tous les colleurs dans une matière.
	"""
	model = Enseignement
	template_name = 'pykol/colloscope/calendrier/matiere.html'

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)

		context['colleur_list'] = Professeur.objects.filter(
			colledetails__colle__colles_ens__enseignements=self.get_object()
			).distinct().order_by('last_name', 'first_name')

		return context

class CalendrierMatiereColleurView(FormMixin, DetailView,
		ProcessFormView):
	"""
	Accès au calendrier d'un colleur dans une matière.
	"""
	model = Professeur
	template_name = 'pykol/colloscope/calendrier/colleur.html'
	pk_url_kwarg = 'colleur_pk'
	form_class = CalendrierColleurFormset

	def get_form_kwargs(self):
		form_kwargs = super().get_form_kwargs()
		form_kwargs['colleur'] = self.get_object()
		form_kwargs['enseignement'] = self.get_enseignement()
		return form_kwargs

	def get_initial(self):
		initial = []
		for colle in Colle.objects.filter(
				colledetails__actif=True,
				colledetails__colleur=self.get_object(),
				enseignement=self.get_enseignement()).order_by('pk'):
			initial.append({
				'colle': colle.pk,
				'debut': colle.details.horaire,
				'duree': colle.duree,
				'duree_etudiant': colle.duree_etudiant,
			})
		return initial

	def get_enseignement(self):
		return get_object_or_404(Enseignement, pk=self.kwargs['matiere_pk'])

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['matiere'] = get_object_or_404(Enseignement, pk=self.kwargs['matiere_pk'])
		return context

	def post(self, *args, **kwargs):
		self.object = self.get_object()
		return super().post(*args, **kwargs)

	def form_valid(self, formset):
		"""
		Sauvegarde de la liste des colles lorsque le formulaire est
		valide.
		"""
		for form in formset.initial_forms:
			colle = form.cleaned_data['colle']
			if not form.has_changed() or colle is None:
				continue

			if form in formset.deleted_forms:
				colle.annuler()
			else:
				colle.ajout_details(horaire=form.cleaned_data['debut'])
				colle.duree = form.cleaned_data['duree']
				colle.duree_etudiant = form.cleaned_data['duree_etudiant']
				colle.save()

		enseignement = self.get_enseignement()
		colleur = self.object

		for form in formset.extra_forms:
			colle = Colle(
				classe=enseignement.classe,
				enseignement=enseignement,
				colles_ens=enseignement.collesenseignement_set.first(),
				duree=form.cleaned_data['duree'],
				duree_etudiant=form.cleaned_data['duree_etudiant'],
			)
			colle.save()
			colle.ajout_details(colleur=colleur,
					horaire=form.cleaned_data['debut'])

		return super().form_valid(formset)

	def get_success_url(self):
		return reverse('colloscope_calendrier_matiere', kwargs={'pk':
			self.get_enseignement().pk})
