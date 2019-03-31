# -*- coding: utf-8

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

from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse

from pykol.models.base import Etudiant, Classe, Enseignement, \
		AbstractPeriode
from .grille import Grille, GrilleLigne

class JuryManager(models.Manager):
	@transaction.atomic
	def create_from_classe(self, classe, periode, **kwargs):
		"""
		Crée un jury pour une classe, en peuplant ce jury de mentions
		vierges pour toutes les matières suivies par les étudiants,
		selon les grilles ECTS présentes dans la base de données.
		"""
		jury = Jury(classe=classe, periode=periode, **kwargs)
		jury.save()

		# On recherche toutes les grilles qui peuvent s'appliquer à
		# cette classe.
		grilles = Grille.objects.filter(code_mef=classe.mef)

		if periode != Jury.PERIODE_ANNEE:
			grilles = grilles.filter(semestre=periode)

		# Pour chaque étudiant, on crée toutes les mentions qui
		# s'appliquent, en fonction des matières suivies par l'étudiant.
		for etudiant in classe.etudiants.all():
			grilles_applicables = grilles.filter_applicables(classe=classe,
					etudiant=etudiant)
			periodes_traitees = set()

			enseignements = Enseignement.objects.filter_etudiant(
				etudiant=etudiant,
				classe=classe,
			)

			for grille in grilles_applicables:
				# On ne garde qu'une grille par semestre
				if grille.semestre in periodes_traitees:
					continue
				periodes_traitees.add(grille.semestre)

				lignes_restantes = set(grille.lignes.all())
				for enseignement in enseignements:
					# On cherche une ligne de la grille qui correspond à
					# cet enseignement. Oui, c'est quadratique, mais vu
					# le tout petit nombre d'enseignements en pratique,
					# il ne semble pas bien pertinent d'optimiser la
					# complexité asymptotique.
					mention = None
					for ligne in lignes_restantes.copy():
						if enseignement.matiere != ligne.matiere.matiere or \
							enseignement.rang_option != ligne.matiere.rang_option or \
							enseignement.modalite_option != ligne.matiere.modalite_option:
							continue

						mention, _ = Mention.objects.credit_or_create(
							etudiant=etudiant, jury=jury,
							enseignement=enseignement,
							grille_ligne__similar=ligne,
							defaults = {
								'grille_ligne': ligne,
								'credits': ligne.credits,
							})

						lignes_restantes.remove(ligne)

					if mention is None:
						# Code exécuté quand un enseignement suivi par
						# un étudiant ne figure dans aucune ligne de la
						# grille. Si l'enseignement est facultatif, on
						# l'ajoute malgré tout à l'attestation ECTS mais
						# sans aucun crédit.
						if enseignement.modalite_option == \
								Enseignement.MODALITE_FACULTATIVE:
							Mention.objects.credit_or_create(
								etudiant=etudiant, jury=jury,
								enseignement=enseignement,
								defaults={
									'credits': 0,
								})

				# Certaines lignes doivent être créées dans tous les
				# cas, même si elles ne correspondent à aucun
				# enseignement suivi par l'étudiant.
				for ligne in lignes_restantes:
					# Dans ce cas, on tente de rattacher la ligne au
					# premier enseignement dont la matière est la bonne.
					if ligne.force_creation:
						enseignement = Enseignement.objects.filter(classe=classe,
							matiere=ligne.matiere.matiere
						).order_by('modalite_option').first()
						Mention.objects.credit_or_create(
							etudiant=etudiant, jury=jury,
							credits=ligne.credits,
							grille_ligne__similar=ligne,
							defaults={
								'grille_ligne': ligne,
								'credits': ligne.credits,
							}
						)

		return jury

class Jury(AbstractPeriode, models.Model):
	"""
	Réunion de jury pour l'attribution des ECTS.
	"""
	date = models.DateTimeField()
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	ETAT_PREVU = 1
	ETAT_TERMINE = 2
	ETAT_CHOICES = (
		(ETAT_PREVU, "prévu"),
		(ETAT_TERMINE, "terminé"),
	)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
		choices=ETAT_CHOICES, default=ETAT_PREVU)

	objects = JuryManager()

	def __str__(self):
		return "Jury {pk}".format(pk=self.pk)

	def get_absolute_url(self):
		return reverse('ects_jury_detail', kwargs={'pk': self.pk,})

class MentionManager(models.Manager):
	@transaction.atomic
	def credit_or_create(self, **kwargs):
		defaults = kwargs['defaults']
		nouvelle_ligne = defaults.pop('grille_ligne', None)

		ligne = kwargs.pop('grille_ligne__similar', None)
		args = tuple()
		if ligne is not None:
			args += (Q(
				grille_lignes__position=ligne.position
			),)
			if ligne.groupe:
				args += (Q(
					grille_lignes__groupe__libelle=ligne.groupe.libelle
				),)

		print(args)
		print(kwargs)
		mention, created = self.filter(*args).get_or_create(**kwargs)
		if not created:
			mention.credits += defaults.get('credits', 0)
			mention.save()
		if nouvelle_ligne:
			mention.grille_lignes.add(nouvelle_ligne)

		return (mention, created)

class Mention(models.Model):
	"""
	Mention attribuée à un étudiant pour une matière donnée et un jury
	donné.

	Une mention peut être globale (il s'agit alors de la mention finale
	accordée pour toute la période du jury) si le champ globale est
	vrai.
	"""
	etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE,
			verbose_name="étudiant")
	jury = models.ForeignKey(Jury, on_delete=models.CASCADE)
	enseignement = models.ForeignKey(Enseignement,
			on_delete=models.CASCADE, blank=True, null=True)

	MENTION_F = MENTION_INSUFFISANT = 0
	MENTION_E = MENTION_PASSABLE = 1
	MENTION_D = MENTION_CONVENABLE = 2
	MENTION_C = MENTION_ASSEZ_BIEN = 3
	MENTION_B = MENTION_BIEN = 4
	MENTION_A = MENTION_TRES_BIEN = 5
	MENTION_CHOICES = (
		(MENTION_F, "insuffisant"),
		(MENTION_E, "passable"),
		(MENTION_D, "convenable"),
		(MENTION_C, "assez bien"),
		(MENTION_B, "bien"),
		(MENTION_A, "très bien"),
	)
	mention = models.PositiveSmallIntegerField(choices=MENTION_CHOICES,
			blank=True, null=True)
	credits = models.PositiveSmallIntegerField(verbose_name="crédits")
	grille_lignes = models.ManyToManyField(GrilleLigne)

	globale = models.BooleanField(help_text="Champ qui indique si "
		"cette mention est la mention globale de l'étudiant pour ce "
		"jury.", default=False)

	objects = MentionManager()

	def __str__(self):
		return "Mention {}".format(self.pk)

	MENTION_LETTRES = ['F', 'E', 'D', 'C', 'B', 'A']
	def get_mention_lettre_display(self):
		return self.MENTION_LETTRES[self.mention]
