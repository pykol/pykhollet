# -*- coding: utf-8 -*-

from django.db import models
from django.core.exceptions import ValidationError

class Note:
	NOTE = 1
	ABSENCE = 2
	ABSENCE_EXCUSEE = 3
	NON_NOTE = 4
	VU = 5
	def __init__(self, initial=None):
		self.kind = NON_NOTE
		self.value = None
		if initial is not None:
			self.set(initial)

	def set(self, value):
		if value == 'a':
			self.kind = ABSENCE
			self.value = 0
		if value == 'ae':
			self.kind = ABSENCE_EXCUSEE
			self.value = None
		if value == 'nn':
			self.kind = NON_NOTE
			self.value = 0
		if value == 'vu':
			self.kind = VU
			self.value = None
		try:
			self.value = float(value)
			self.kind = NOTE
		except ValueError:
			raise ValueError("Une note doit être soit un nombre, soit l'une des valeur particulières suivantes: 'nn' (non noté, compte dans une moyenne), 'vu' (non noté, ne compte pas dans une moyenne), 'a' (absence, compte dans une moyenne), 'ae' (absence excusée, ne compte pas dans une moyenne)")

	def __repr__(self):
		if self.kind == NOTE:
			return repr(self.value)
		if self.kind == ABSENCE:
			return 'a'
		if self.kind == ABSENCE_EXCUSEE:
			return 'ae'
		if self.kind == NON_NOTE:
			return 'nn'
		if self.kind == VU:
			return 'vu'

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