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

from functools import total_ordering
from django.db import models
from django.core.exceptions import ValidationError

@total_ordering
class Note:
	NOTE = 1
	NON_NOTE = 2
	VU = 3
	ABSENCE = 4
	ABSENCE_EXCUSEE = 5

	def __init__(self, initial=None):
		self.kind = Note.NON_NOTE
		self.value = None
		if initial is not None:
			self.set(initial)

	def set(self, value):
		if value == 'a':
			self.kind = Note.ABSENCE
			self.value = 0
		elif value == 'ae':
			self.kind = Note.ABSENCE_EXCUSEE
			self.value = None
		elif value == 'nn':
			self.kind = Note.NON_NOTE
			self.value = 0
		elif value == 'vu':
			self.kind = Note.VU
			self.value = None
		else:
			try:
				self.value = float(value)
				self.kind = Note.NOTE
			except (ValueError, TypeError):
				raise ValueError("Une note doit être soit un nombre, "
					"soit l'une des valeurs particulières suivantes: "
					"'nn' (non noté, compte dans une moyenne), "
					"'vu' (non noté, ne compte pas dans une moyenne), "
					"'a' (absence, compte dans une moyenne), "
					"'ae' (absence excusée, ne compte pas dans une moyenne)")

	def __repr__(self):
		if self.kind == Note.NOTE:
			return repr(self.value)
		if self.kind == Note.ABSENCE:
			return 'a'
		if self.kind == Note.ABSENCE_EXCUSEE:
			return 'ae'
		if self.kind == Note.NON_NOTE:
			return 'nn'
		if self.kind == Note.VU:
			return 'vu'

	def compte_dans_moyenne(self):
		return self.value is not None

	def est_note(self):
		return self.kind == Note.NOTE

	def __add__(self, note):
		# Le premier Moyenne() de la liste permet d'appeler ensuite la
		# méthode __add__ de la classe Moyenne au lieu de celle de Note.
		return Moyenne() + self + note

	def __eq__(self, note):
		if not isinstance(note, Note):
			try:
				note = Note(note)
			except ValueError:
				return False

		if self.kind == Note.NOTE:
			return note.kind == Note.NOTE and self.value == note.value
		else:
			return self.kind == note.kind

	def __le__(self, note):
		if self.kind == note.NOTE == note.kind:
			return self.value <= note.value
		else:
			return self.kind >= note.kind

class Moyenne(Note):
	def __init__(self):
		self.points = None
		self.nb_notes = 0
		self.kind = Note.NON_NOTE

	@property
	def value(self):
		if self.points is not None:
			return self.points / self.nb_notes
		else:
			return None

	def __add__(self, note):
		if not isinstance(note, Note):
			note = Note(note)

		res = Moyenne()

		res.points = self.points

		if self.nb_notes == 0:
			res.kind = note.kind

		if note.compte_dans_moyenne():
			res.nb_notes = self.nb_notes + 1
			res.points = int(self.points or 0) + int(note.value or 0)
			res.kind = min(self.kind, note.kind)

		return res

	def __iadd__(self, note):
		if not isinstance(note, Note):
			note = Note(note)

		if self.nb_notes == 0:
			self.kind = note.kind

		if note.compte_dans_moyenne():
			self.nb_notes = self.nb_notes + 1
			self.points = int(self.points or 0) + int(note.value or 0)
			self.kind = min(self.kind, note.kind)

		return self

class NoteField(models.Field):
	description = "Note représentant une évaluation chiffrée"

	def __init__(self, *args, **kwargs):
		# https://randomascii.wordpress.com/2012/03/08/float-precisionfrom-zero-to-100-digits-2/
		kwargs['max_length'] = 21
		super(NoteField, self).__init__(*args, **kwargs)

	def deconstruct(self):
		name, path, args, kwargs = super(NoteField, self).deconstruct()
		del kwargs["max_length"]
		return name, path, args, kwargs

	def from_db_value(self, value, expression, connection, context):
		if value is None:
			return value
		return Note(value)

	def to_python(self, value):
		if isinstance(value, Note) or value is None:
			return value

		try:
			return Note(value)
		except ValueError as e:
			raise ValidationError(e.message, code='invalid',
					params={'value': value})

	def get_prep_value(self, note):
		if note.kind == Note.NOTE:
			return '{:.17g}'.format(note.value)
		else:
			return repr(note)

	def get_internal_type(self):
		return 'CharField'

	def formfield(self, **kwargs):
		defaults = {'form_class': None,} #XXX
		defaults.update(kwargs)
		return super(NoteField, self).formfield(**defaults)
