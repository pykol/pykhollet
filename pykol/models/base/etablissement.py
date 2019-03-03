# -*- coding:utf8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018-2019 Florian Hatat
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

from django.db import models
from django.core.validators import validate_comma_separated_integer_list

from pykol.models.fields import Lettre23Field
import pykol.lib.files
from pykol.models.comptabilite import Compte

class Academie(models.Model):
	"""
	Académie
	"""
	id = models.PositiveSmallIntegerField(primary_key=True,
			verbose_name="numéro")
	nom = models.CharField(max_length=100)
	nom_complet = models.CharField(max_length=100)
	slug = models.SlugField()
	departements = models.CharField(max_length=100, verbose_name="départements",
			validators=[validate_comma_separated_integer_list])

	compte_dotation = models.ForeignKey(Compte,
			on_delete=models.PROTECT, related_name='rectorat')
	compte_paiement = models.ForeignKey(Compte,
			on_delete=models.PROTECT, related_name='asie')

	class Meta:
		verbose_name = "académie"
		verbose_name_plural = "académies"

	def __str__(self):
		return self.nom_complet

class Etablissement(models.Model):
	"""
	Établissement d'enseignement
	"""
	#XXX sensibilité à la casse de la lettre code UAI
	numero_uai = Lettre23Field(length=8, unique=True,
			verbose_name="UAI", primary_key=True)
	appellation = models.CharField(max_length=200)
	denomination = models.CharField(max_length=100)
	adresse = models.TextField(
			verbose_name="adresse de l'établissement",
			blank=True)
	academie = models.ForeignKey(Academie, verbose_name="académie",
			null=True, blank=True,
			on_delete=models.PROTECT)
	email = models.EmailField(blank=True)

	NATURE_UAI=(
			(101,"École maternelle"),
			(102,"École maternelle annexe d'ESPÉ"),
			(103,"École maternelle d'application"),
			(111,"École maternelle spécialisée"),
			(151,"École élémentaire"),
			(152,"École élémentaire annexe d'ESPÉ"),
			(153,"École élémentaire d'application"),
			(160,"École de plein air"),
			(162,"École élémentaire spécialisée"),
			(169,"École régionale du premier degré"),
			(170,"École sans effectif permanent"),
			(300,"Lycée d'enseignement général et technologique"),
			(301,"Lycée d'enseignement technologique"),
			(302,"Lycée d'enseignement général"),
			(306,"Lycée polyvalent"),
			(310,"Lycée climatique"),
			(312,"École secondaire spécialisée (second cycle)"),
			(315,"Établissement expérimental"),
			(320,"Lycée professionnel"),
			(332,"École professionnelle spécialisée"),
			(334,"Section d'enseignement professionnel"),
			(335,"Section d'enseignement général ou technologique"),
			(340,"Collège"),
			(349,"Établissement de réinsertion scolaire"),
			(350,"Collège climatique"),
			(352,"Collège spécialisé"),
			(370,"Établissement régional d'enseignement adapté"),
			(390,"Section d'enseignement général et professionnel adapté"),
		)
	nature_uai = models.PositiveSmallIntegerField(choices=NATURE_UAI)

	chef_etablissement = models.ForeignKey('User', blank=True, null=True,
			on_delete=models.SET_NULL,
			related_name='etablissement_proviseur',
			verbose_name="chef d'établissement")
	tampon_etablissement = models.ImageField(blank=True, null=True,
			verbose_name="tampon de l'établissement",
			storage=pykol.lib.files.private_storage,
			upload_to='tampon_etablissement/')

	ville = models.CharField(max_length=100, blank=True)

	# Compte de dotation en colles
	compte_colles = models.ForeignKey(Compte, blank=True, null=True,
			on_delete=models.PROTECT,
			related_name='etablissement_dotation')
	# Compte racine des relevés de colles
	compte_releves = models.ForeignKey(Compte, blank=True, null=True,
			on_delete=models.PROTECT,
			related_name='etablissement_releves')

	class Meta:
		ordering = ['numero_uai']
		verbose_name = "établissement"
		verbose_name_plural = "établissements"

	def __str__(self):
		return self.appellation

	def get_absolute_url(self):
		from django.urls import reverse
		return reverse('etablissement.views.detail', args=[self.uai])
