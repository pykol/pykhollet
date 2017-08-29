# -*- coding: utf-8

from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction

from base.models import Classe
from colles.models import Semaine
from colles.forms import SemaineFormSet, SemaineNumeroGenerateurForm

@login_required
def colloscope_home(request):
	return render(request, 'base.html')

@login_required
def colloscope(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('matiere', 'jour', 'debut')
	return render(request, 'colloscope.html',
			context={
				'classe': classe,
				'semaines': semaines,
				'creneaux' : creneaux,
				})

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

	formset_prefix = "semaines"

	if request.method == 'POST':
		formset = SemaineFormSet(request.POST, prefix=formset_prefix)
		genform = SemaineNumeroGenerateurForm(request.POST, prefix="gen")
		formset_data = formset.data.copy()

		if genform.is_valid() and genform.cleaned_data['actif']:
			formset.full_clean()

			id_colle = 0

			for id_semaine, form in enumerate(formset.forms):
				for field in ('debut', 'fin', 'est_colle',):
					formset_data['semaines-{}-{}'.format(id_semaine,
						field)] = form.cleaned_data[field]

				if form.cleaned_data['est_colle']:
					formset_data['semaines-{}-numero'.format(id_semaine)] = \
							genform.cleaned_data['format'].format(
							numero=id_colle + 1,
							quinzaine=id_colle // 2 + 1,
							parite=(id_colle + 1) % 2,
							parite_alpha='AB'[id_colle % 2])

					id_colle += 1

			for field in ('TOTAL_FORMS', 'INITIAL_FORMS',
					'MAX_NUM_FORMS',):
				field_name = '{}-{}'.format(formset_prefix, field)
				formset_data[field_name] = formset.data[field_name]

			formset = SemaineFormSet(formset_data, prefix=formset_prefix)

		if formset.is_valid():
			with transaction.atomic():
				for id_semaine, data in enumerate(formset.cleaned_data):
					if not data['est_colle']:
						formset_data['{}-{}-numero'.format(formset_prefix,
							id_semaine)] = None

					if data['semaine'] and not data['est_colle']:
						formset_data['{}-{}-semaine'.format(formset_prefix,
							id_semaine)] = None
						data['semaine'].delete()

					if not data['semaine'] and data['est_colle']:
						semaine = Semaine(debut=data['debut'],
								fin=data['fin'],
								numero=data['numero'],
								classe=classe)
						semaine.save()
						formset_data['{}-{}-semaine'.format(formset_prefix,
							id_semaine)] = semaine.pk

					if data['semaine'] and data['est_colle']:
						semaine = data['semaine']
						semaine.debut = data['debut']
						semaine.fin = data['fin']
						semaine.numero = data['numero']
						semaine.save()

			formset = SemaineFormSet(formset_data,
					prefix=formset_prefix,
					form_kwargs={'classe': classe})

	else:
		annee = classe.annee
		# Calcul des semaines de toute l'année
		lundi = annee.debut - timedelta(days=annee.debut.weekday())
		toutes_semaines = []
		while lundi < annee.fin:
			try:
				semaine = Semaine.objects.get(debut=lundi)
				toutes_semaines.append({
					'debut': semaine.debut,
					'fin': semaine.fin,
					'est_colle': True,
					'numero': semaine.numero,
					'semaine': semaine,
					})
			except Semaine.DoesNotExist:
				toutes_semaines.append({
					'debut': lundi,
					'fin': lundi + timedelta(days=6),
					'est_colle': False,
					'numero': None,
					})
			lundi += timedelta(days=7)
		formset = SemaineFormSet(initial=toutes_semaines,
				prefix=formset_prefix)
		genform = SemaineNumeroGenerateurForm(prefix="gen")

	return render(request, 'semaines.html',
			context={
				'classe': classe,
				'formset': formset,
				'genform': genform,
				})

from base.navigation import nav
nav.register("Colloscope", "colloscope_home", icon="calendar",
		name="colloscope")
