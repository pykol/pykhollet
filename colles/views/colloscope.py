# -*- coding: utf-8

from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction

from base.models import Classe
from colles.models import Semaine
from colles.forms import SemaineFormSet

@login_required
def colloscope_home(request):
	return render(request, 'base.html')

@login_required
def colloscope(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	return render(request, 'base.html')

@login_required
def trinomes(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	trinomes = classe.trinomes
	return render(request, 'base.html')

@login_required
def create_trinome(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	return render(request, 'base.html')

@login_required
def semaines(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if request.method == 'POST':
		formset = SemaineFormSet(request.POST)
		if formset.is_valid():
			with transaction.atomic():
				for data in formset.cleaned_data:
					if data['est_colle']:
						semaine = Semaine(debut=data['debut'],
								fin=data['fin'],
								numero=data['numero'],
								classe=classe)
						semaine.save()
	else:
		annee = classe.annee
		# Calcul des semaines de toute l'année
		lundi = annee.debut - timedelta(days=annee.debut.weekday())
		toutes_semaines = []
		while lundi < annee.fin:
			toutes_semaines.append({
				'debut': lundi,
				'fin': lundi + timedelta(days=6),
				'est_colle': False,
				'numero': None,
				})
			lundi += timedelta(days=7)
		formset = SemaineFormSet(initial=toutes_semaines)

	return render(request, 'semaines.html',
			context={
				'classe': classe,
				'formset': formset,
				})

from base.navigation import nav
nav.register("Colloscope", "colloscope_home", icon="calendar")
