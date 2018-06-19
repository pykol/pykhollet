# -*- coding: utf-8 -*-

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


from django.test import TestCase
from django.core.exceptions import ValidationError
from pykol.uppercasecharfield import validateur_lettre23

class ValidationUaiTests(TestCase):
	def test_lettre_code_correcte_1(self):
		self.assertIsNone(validateur_lettre23("0021593W"))

	def test_lettre_code_incorrecte(self):
		with self.assertRaises(ValidationError):
			validateur_lettre23("0740003A")
