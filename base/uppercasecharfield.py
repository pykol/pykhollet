# -*- coding: utf-8 -*-

import string
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

class UppercaseCharField(models.CharField):
	description = "Uppercase char field"

	def __init__(self, *args, **kwargs):
		super(UppercaseCharField, self).__init__(*args, **kwargs)

	def get_prep_value(self, value):
		return super(UppercaseCharField, self).get_prep_value(value).upper()

def validateur_lettre23(uai):
	code_lettre = int(uai[:-1]) % 23
	alphabet = [l for l in string.ascii_lowercase if l not in ('i','o','q')]
	if uai[-1].lower() != alphabet[code_lettre]:
		raise ValidationError(_("Le numéro %(uai)s comporte une erreur"), params={'uai':uai})

class Lettre23Field(UppercaseCharField):
	description = "Numéro suivi d'une lettre de contrôle"

	def __init__(self, *args, **kwargs):
		regex = "\d{{{0},{0}}}[a-zA-Z]".format(kwargs['length'] - 1)
		self.length = kwargs['length']
		kwargs['max_length'] = kwargs['length']
		kwargs.setdefault('validators', [])
		kwargs['validators'].append(RegexValidator(regex=regex,
			message="Le code doit être constitué de {} chiffres suivis d'une lettre code".format(kwargs['length'] - 1)))
		kwargs['validators'].append(validateur_lettre23)
		del kwargs['length']
		super(Lettre23Field, self).__init__(*args, **kwargs)

	def deconstruct(self):
		name, path, args, kwargs = super(Lettre23Field, self).deconstruct()

		kwargs['length'] = self.length
		del kwargs['max_length']

		try:
			kwargs['validators'].remove(validateur_lettre23)
			#XXX retirer RegexValidator
		except ValueError:
			pass

		return name, path, args, kwargs
