# -*- coding:utf8 -*-

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

from datetime import timedelta, datetime

from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from pykol.models.base import Classe, Professeur, Matiere, Etudiant, \
		Enseignement, Periode
from pykol.models.fields import NoteField
from pykol.models.comptabilite import Mouvement

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class AbstractBaseColle(models.Model):
	"""
	Classe abstraite qui contient les champs communs entre une colle et
	un créneau de colle.
	"""
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	enseignement = models.ForeignKey(Enseignement, blank=True,
			null=True, on_delete=models.SET_NULL)
	colles_ens = models.ForeignKey('CollesEnseignement', blank=True,
			null=True, on_delete=models.SET_NULL)
	duree = models.DurationField(verbose_name="durée",
			default=timedelta(hours=1))
	duree_etudiant = models.DurationField(
			verbose_name="durée de passage par étudiant",
			blank=True, null=True)

	MODE_INTERROGATION = 0
	MODE_TD = 1
	MODE_CHOICES = (
			(MODE_INTERROGATION, "interrogation"),
			(MODE_TD, "travaux dirigés"),
		)
	mode = models.PositiveSmallIntegerField(
			verbose_name="mode de déroulement",
			choices=MODE_CHOICES,
			default=MODE_INTERROGATION)

	class Meta:
		abstract = True

	def basecolle_fields(self):
		"""Dictionnaire qui contient les valeurs des champs de base
		définis par la classe AbstractBaseColle. C'est un raccourci qui
		permet de reprendre rapidement les informations d'un Creneau
		pour créer une Colle."""
		return {
				'classe': self.classe,
				'enseignement': self.enseignement,
				'colles_ens': self.colles_ens,
				'duree': self.duree,
				'mode': self.mode,
			}


class ColleQuerySet(models.QuerySet):
	@transaction.atomic
	def update_or_create_from_creneau(self, creneau, semaine,
			trinome=None):
		"""
		Créer une colle sur le modèle du créneau, sur la semaine
		donnée et pour le groupe donné.

		On considère que la colle est identifiée par sa semaine et son
		créneau. Si le trinôme change, on met simplement à jour la
		colle.
		"""
		colle_data = creneau.basecolle_fields()
		if trinome is not None:
			colle_data['groupe'] = trinome

		# Pour un TD, on prend la durée donnée par les horaires
		if creneau.mode == creneau.MODE_TD:
			colle_data['duree'] = \
					datetime.combine(datetime.min, creneau.fin) - \
					datetime.combine(datetime.min, creneau.debut)

		#TODO intégration de la comptabilité

		(colle, created) = self.update_or_create(
				creneau=creneau,
				semaine=semaine,
				defaults=colle_data)

		# On accepte uniquement la modification si la colle n'a pas
		# encore été effectuée.
		if colle.etat in (Colle.ETAT_BROUILLON, Colle.ETAT_PREVUE):
			colle.ajout_details(
				horaire=semaine.horaire_creneau(creneau),
				salle=creneau.salle,
				colleur=creneau.colleur,
				etudiants=trinome.etudiants.all())

		return (colle, created)

	def synchro_creneau(self):
		"""
		Mise à jour des colles de ce QuerySet pour répercuter les
		modifications de leur créneau.
		"""
		for colle in self.filter(creneau__isnull=False,
				semaine__isnull=False):
			colle.ajout_details(
					horaire=colle.semaine.horaire_creneau(colle.creneau),
					salle=colle.creneau.salle,
					colleur=colle.creneau.colleur)

	def synchro_trinome(self):
		"""
		Mise à jour des colles de ce QuerySet pour répercuter les
		modifications sur le trinome de colle
		"""
		for colle in self.filter(groupe__isnull=False):
			colle.ajout_details(etudiants=colle.groupe.etudiants.all())

class ColleManager(models.Manager):
	def get_queryset(self):
		return ColleQuerySet(self.model, using=self._db)

	def update_or_create_from_creneau(self, *args, **kwargs):
		return self.get_queryset().update_or_create_from_creneau(*args,
				**kwargs)

	def synchro_creneau(self):
		return self.get_queryset().synchro_creneau()

	def synchro_trinome(self):
		return self.get_queryset().synchro_trinome()

class ColleConfirmeeManager(ColleManager):
	"""
	Gestionnaire personnalisé sur les colles qui permet de n'afficher
	que les colles confirmées.
	"""
	def get_queryset(self):
		return super().get_queryset().exclude(etat=Colle.ETAT_BROUILLON)

class Colle(AbstractBaseColle):
	"""
	Représentation d'une séance de colle
	"""
	creneau = models.ForeignKey('Creneau', blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="créneau")
	semaine = models.ForeignKey('Semaine', blank=True, null=True,
			on_delete=models.SET_NULL)

	ETAT_BROUILLON = 5
	ETAT_PREVUE = 0
	ETAT_NOTEE = 1
	ETAT_EFFECTUEE = 4
	ETAT_RELEVEE = 2
	ETAT_ANNULEE = 3
	ETAT_CHOICES = (
			(ETAT_BROUILLON, "brouillon"),
			(ETAT_PREVUE, "prévue"),
			(ETAT_NOTEE, "notée"),
			(ETAT_EFFECTUEE, "effectuée"),
			(ETAT_RELEVEE, "relevée"),
			(ETAT_ANNULEE, "annulée"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_PREVUE)
	groupe = models.ForeignKey('Trinome', blank=True, null=True,
			on_delete=models.SET_NULL)
	releve = models.ForeignKey('ColleReleve', blank=True, null=True,
			on_delete=models.SET_NULL)

	# On remplace le gestionnaire objects, mais en prenant soin de
	# laisser le gestionnaire par défaut all_objects en première
	# position (c'est lui qui est utilisé par Django comme gestionnaire
	# de base).
	all_objects = ColleManager()
	objects = ColleConfirmeeManager()

	@property
	def details(self):
		"""Renvoie le dernier ColleDetails actif pour cette colle"""
		return self.colledetails_set.get(actif=True)

	@property
	def colleur(self):
		"""Renvoie le colleur qui assure cette colle"""
		return self.details.colleur

	def _get_duree_etudiant(self):
		"""
		Détermine la durée d'interrogation par étudiant

		Cette méthode utilise la valeur du champ duree_etudiant, s'il
		n'est pas nul, ou bien la durée par défaut de l'objet
		CollesEnseignement lié.
		"""
		if self.duree_etudiant is None:
			return self.colles_ens.duree_frequentielle
		else:
			return self.duree_etudiant

	def _update_duree(self):
		# On laisse la durée par défaut pour le mode TD
		if self.mode == Colle.MODE_TD:
			return

		if self.colles_ens.frequence == self.colles_ens.FREQUENCE_HEBDOMADAIRE:
			self.duree = timedelta(hours=1)
		else:
			self.duree = self.details.eleves.count() * \
					self._get_duree_etudiant()
		self.save()

	def __str__(self):
		return "Colle du {date} en {classe}".format(
			date=self.details.horaire, classe=self.classe)

	@transaction.atomic
	def ajout_details(self, horaire=None, salle='', colleur=None,
			etudiants=[]):
		"""
		Ajouter un ColleDetails qui met à jour le précédent.

		Si les étudiants, le colleur ou l'horaire ne sont pas précisés, on
		reprend ceux qui existaient déjà dans le ColleDetails précédent.

		Si la salle n'est pas indiquée, on ne reprend l'ancienne salle
		que si l'horaire de la colle n'a pas changé. Sinon, la
		réservation de salle n'est pas garantie et il vaut mieux laisser
		le champ vide.

		En revanche, dans le cas où la salle n'était auparavant pas
		connue et qu'il s'agit de la seule information renseignée lors
		de l'appel, on ne crée pas de nouvelle ligne ColleDetails.
		(C'est le cas d'un déplacement de colle par le professeur avec
		réservation un peu plus tard de la salle par la direction.)

		Cette méthode renvoie le nouvel objet ColleDetails actif pour la
		colle.
		"""
		try:
			ancien_detail = self.details

			if not colleur:
				colleur = ancien_detail.colleur
			if not etudiants:
				etudiants = ancien_detail.eleves.all()
			if not horaire:
				horaire = ancien_detail.horaire

			# On reprend la salle uniquement quand l'horaire n'a pas
			# changé.
			if not salle and horaire == ancien_detail.horaire:
				salle = ancien_detail.salle

			colleur_modifie = colleur != ancien_detail.colleur
			anciens_etudiants = set(ancien_detail.eleves.all())
			etudiants_modifies = set(etudiants) != anciens_etudiants

			detail_modifie = \
					colleur_modifie or etudiants_modifies or \
					horaire != ancien_detail.horaire

			# Cas où l'on ajoute une salle qui n'était précédemment pas
			# renseignée. Dans ce cas, on ne crée pas de nouveau
			# ColleDetails mais on met à jour l'actuel.
			if not detail_modifie and \
					not ancien_detail.salle and salle:
				ancien_detail.salle = salle
				ancien_detail.save()
				return ancien_detail

			detail_modifie = detail_modifie or \
				ancien_detail.salle != salle

		except ColleDetails.DoesNotExist:
			ancien_detail = None
			detail_modifie = True
			colleur_modifie = True
			etudiants_modifies = True
			anciens_etudiants = set()

		# Ajout d'un nouveau ColleDetails s'il y a des modifications
		if detail_modifie:
			self.colledetails_set.update(actif=False)

			detail = ColleDetails(colle=self, horaire=horaire, salle=salle,
				colleur=colleur)
			detail.save()
			detail.eleves.set(etudiants)

			self._update_duree()

		# Mise à jour des écritures comptables s'il y a un changement de
		# colleur et/ou d'effectif sur la colle, ou en cas de première
		# programmation de la colle. Pour cela, on commence par renvoyer
		# la dotation sur le compte de la matière, et on re-créditera
		# ensuite comme s'il s'agissait d'une nouvelle colle.
		if ancien_detail is not None and (colleur_modifie or
				anciens_etudiants != len(set(etudiants))):
			self.annuler_mouvement()

		# Dotation de la colle. Ceci peut lever une exception, qui fait
		# tout échouer.
		self.comptabiliser()

		return self.details

	def get_absolute_url(self):
		return reverse('colle_detail', kwargs={'pk': self.pk})

	@property
	def matiere(self):
		return self.enseignement.matiere

	@property
	def est_effectuee(self):
		return self.etat in (self.ETAT_NOTEE, self.ETAT_EFFECTUEE, self.ETAT_RELEVEE)

	@property
	def duree_interrogation(self):
		if self.mode == Colle.MODE_TD:
			return self.duree
		else:
			return len(self.details.eleves.all()) * self._get_duree_etudiant()

	def comptabiliser(self, compte_source=None, valider=True):
		"""
		Création d'un mouvement comptable qui débite l'enveloppe de
		colles de la matière et crédite le compte du professeur.

		Cette méthode ne vérifie pas si le mouvement n'a pas déjà été
		créé précédemment.
		"""
		if compte_source is None:
			compte_source = self.colles_ens.compte_colles

		mv = Mouvement.objects.virement(
			date=timezone.now(),
			annee=self.classe.annee,
			colle=self,
			duree=self.duree,
			duree_interrogation=self.duree_interrogation,
			compte_debit=compte_source,
			compte_credit=self.colleur.compte_prevu,
			motif=str(self),
		)
		if valider:
			mv.valider()
		return mv

	def effectuer(self):
		"""
		Méthode qui marque la colle comme étant effectuée. Si elle était
		déjà effectuée, cette méthode ne fait rien.
		"""
		if self.est_effectuee:
			return

		if self.mode == self.MODE_TD:
			self.etat = self.ETAT_EFFECTUEE
		else:
			self.etat = self.ETAT_NOTEE

		# Créditer le compte du colleur pour le paiement
		Mouvement.objects.virement(
			date=timezone.now(),
			annee=self.classe.annee,
			colle=self,
			duree=self.duree,
			duree_interrogation=self.duree_interrogation,
			compte_debit=self.colleur.compte_prevu,
			compte_credit=self.colleur.compte_effectue,
			motif=str(self)).valider()

		self.save()

	def annuler_mouvement(self):
		# Recherche du mouvement actuel qui dote cette colle.
		old_mv = Mouvement.objects.get(colle=self,
				lignes__lettrage__isnull=True,
				lignes__duree__gte=timedelta())
		retour_mv = old_mv.virement_retour()
		retour_mv.colle = self
		retour_mv.save()
		retour_mv.valider()

	def annuler(self):
		"""
		Méthode qui annule une colle qui n'a pas encore été effectuée.
		Si elle a été effectuée, on ne change rien.
		"""
		if self.est_effectuee:
			return

		self.etat = self.ETAT_ANNULEE
		self.annuler_mouvement()
		self.save()

class ColleDetails(models.Model):
	"""
	Détails sur le déroulement d'une colle (date, heure, lieu, élèves).

	Un seul ColleDetails peut être actif par colle. La liste des
	ColleDetails pour une même colle permet de conserver l'historique
	des modifications apportées à une colle (déplacement, changement de
	groupe ou de colleur).
	"""
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE,
			db_index=True)
	horaire = models.DateTimeField()
	salle = models.CharField(max_length=30, blank=True)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL, db_index=True)
	eleves = models.ManyToManyField(Etudiant, blank=True,
			verbose_name="élèves", db_index=True)
	actif = models.BooleanField(default=True)

	class Meta:
		verbose_name = "détails de la colle"
		verbose_name_plural = "détails de la colle"

class ColleNote(models.Model):
	"""
	Note attribuée à une colle pour un étudiant.
	"""
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE,
			db_index=True)
	eleve = models.ForeignKey(Etudiant, on_delete=models.CASCADE,
			db_index=True)
	note = NoteField()
	horaire = models.DateTimeField()
	duree = models.DurationField(verbose_name="durée d'interrogation")

	class Meta:
		verbose_name = "note de colle"
		verbose_name_plural = "notes de colle"

class PeriodeNotation(Periode):
	"""
	Période personnalisée pour le calcul des moyennes de colles.

	Ce modèle permet de calculer des moyennes d'oral séparées pour
	chaque période de l'année définie par le professeur de la classe.

	Chaque période est valable pour une seule matière dans une classe
	donnée. Chaque professeur de la classe peut définir des périodes de
	notation indépendamment de ses collègues des autres matières.
	"""
	enseignement = models.ForeignKey(Enseignement,
			on_delete=models.CASCADE)
