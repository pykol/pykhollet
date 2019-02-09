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

from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone
#from django.contrib.auth import get_user_model
#User = get_user_model()

from mptt.models import MPTTModel, TreeForeignKey

class Compte(MPTTModel):
	nom = models.CharField(max_length=100)
	parent = TreeForeignKey('self', on_delete=models.CASCADE,
			null=True, blank=True, related_name='sous_comptes')
	proprietaire = models.ForeignKey('User', blank=True, null=True,
			on_delete=models.SET_NULL)

	CATEGORIE_DEPENSES = 0
	CATEGORIE_ACTIFS = 1
	CATEGORIE_REVENUS = 2
	CATEGORIE_DETTES = 3
	CATEGORIE_FONDS_PROPRES = 4
	CATEGORIE_CHOICES = (
		(CATEGORIE_DEPENSES, "compte de dépenses"),
		(CATEGORIE_ACTIFS, "compte d'actifs"),
		(CATEGORIE_REVENUS, "compte de revenus"),
		(CATEGORIE_DETTES, "compte de dettes"),
		(CATEGORIE_FONDS_PROPRES, "compte de fonds propres"),
	)
	categorie = models.SmallIntegerField(verbose_name="type de compte",
			choices=CATEGORIE_CHOICES)

	def solde(self, annee):
		"""
		Calcul du solde du compte pour l'année donnée en paramètre.

		Cette méthode renvoie une liste de dictionnaires, chaque
		dictionnaire donne la durée totale et la durée d'interrogation
		pour un taux donné.
		"""
		return self.lignes.filter(mouvement__annee=annee
				).values('taux').aggregate(duree=models.Sum('duree'),
				duree_interrogation=models.Sum('interrogation')).values()

class Mouvement(models.Model):
	"""
	Transfert d'heures de colles entre comptes.

	Les mouvements d'heures sont suivis en comptabilité double : pour
	chaque mouvement, on trouve une ou plusieurs lignes de débit sur
	certains d'autres et des lignes de crédit sur d'autres comptes.

	Un mouvement d'heures est une liste de MouvementLigne dont le solde
	doit être équilibré (somme à zéro).
	"""
	annee = models.ForeignKey('Annee', on_delete=models.CASCADE)
	date = models.DateTimeField(default=timezone.now)
	motif = models.CharField(max_length=100)

	# Lien vers une éventuelle colle à l'origine de ce mouvement
	colle = models.ForeignKey('Colle', on_delete=models.SET_NULL,
			blank=True, null=True)

	ETAT_BROUILLON = 0
	ETAT_VALIDE = 1
	ETAT_CHOICES = (
		(ETAT_BROUILLON, "brouillon"),
		(ETAT_VALIDE, "validé"),
	)
	etat = models.SmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_BROUILLON)

	def solde(self):
		return self.lignes.aggregate(duree=models.Sum('duree'),
				duree_interrogation=models.Sum('duree_interrogation'))

	def est_equilibre(self):
		solde = self.solde()
		return solde['duree'] == timedelta() and \
				solde['duree_interrogation'] == timedelta()

class Lettrage(models.Model):
	"""
	Rapprochement de lignes de mouvements.

	Ceci permet de pointer des mouvements qui ont un rapport les uns
	avec les autres. Par exemple pour le compte d'un professeur donné :
	* lorsqu'il effectue une colle, son compte personnel est crédité du
	  nombre d'heures correspondant ;
	* lorsqu'une mise en paiement est effectuée sur ASIE, le compte
	  personnel est débité du nombre d'heures payées ;
	* on peut alors lettrer les lignes de crédit avec cette dernière
	  ligne de débit. Ceci indique alors quelles heures ont été mises en
	  paiement et à quelle date.
	"""
	date = models.DateTimeField(default=timezone.now)

class ColleDureeTaux(models.Model):
	TAUX_1A_INF20 = 1
	TAUX_1A_INF35 = 2
	TAUX_1A_SUP36 = 3
	TAUX_2A_INF20 = 4
	TAUX_2A_INF35 = 5
	TAUX_2A_SUP36 = 6

	TAUX_CHOICES = (
		(TAUX_1A_INF20, "1è année - Moins de 20 étudiants"),
		(TAUX_1A_INF35, "1è année - Entre 21 et 35 étudiants"),
		(TAUX_1A_SUP36, "1è année - Plus de 35 étudiants"),
		(TAUX_2A_INF20, "2è année - Moins de 20 étudiants"),
		(TAUX_2A_INF35, "2è année - Entre 21 et 35 étudiants"),
		(TAUX_2A_SUP36, "2è année - Plus de 35 étudiants"),
		)
	taux = models.PositiveSmallIntegerField(verbose_name="taux",
			choices=TAUX_CHOICES)
	duree_interrogation = models.DurationField(
			verbose_name="durée d'interrogation", default=timedelta)
	duree = models.DurationField(verbose_name="nombre d'heures",
			default=timedelta)

	class Meta:
		abstract = True

class MouvementLigne(ColleDureeTaux):
	"""
	Ligne d'un mouvement sur un compte.

	Dans un même mouvement, la somme de toutes les lignes doit être
	nulle.
	"""
	compte = models.ForeignKey(Compte, on_delete=models.CASCADE,
			related_name='lignes')
	mouvement = models.ForeignKey(Mouvement, related_name='lignes',
			on_delete=models.CASCADE)
	motif = models.CharField(max_length=100)
	lettrage = models.ForeignKey(Lettrage, related_name='lignes',
			blank=True, null=True, on_delete=models.SET_NULL)
