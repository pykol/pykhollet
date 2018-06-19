# -*- coding:utf8 -*-
from django.db import models
from django.core.validators import validate_comma_separated_integer_list

from pykol.uppercasecharfield import Lettre23Field

class Academie(models.Model):
	"""
	Académie
	"""
	nom = models.CharField(max_length=100)
	slug = models.SlugField()
	departements = models.CharField(max_length=100, verbose_name="départements",
			validators=[validate_comma_separated_integer_list])

	class Meta:
		verbose_name = "académie"
		verbose_name_plural = "académies"

	def __str__(self):
		return self.nom

class Etablissement(models.Model):
	"""
	Établissement d'enseignement
	"""
	#XXX sensibilité à la casse de la lettre code UAI
	numero_uai = Lettre23Field(length=8, unique=True,
			verbose_name="UAI", primary_key=True)
	appellation = models.CharField(max_length=100)
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

	class Meta:
		ordering = ['numero_uai']
		verbose_name = "établissement"
		verbose_name_plural = "établissements"

	def __str__(self):
		return self.appellation

	def get_absolute_url(self):
		from django.urls import reverse
		return reverse('etablissement.views.detail', args=[self.uai])
