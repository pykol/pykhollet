# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.exceptions import ValidationError
from .models.etablissement import validateur_lettre23

class ValidationUaiTests(TestCase):
	def test_lettre_code_correcte_1(self):
		self.assertIsNone(validateur_lettre23("0021593W"))

	def test_lettre_code_incorrecte(self):
		with self.assertRaises(ValidationError):
			validateur_lettre23("0740003A")
