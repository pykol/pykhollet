# -*- coding: utf-8 -*-

import re

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError

# From https://gist.github.com/eerien/7002396

class MinLengthValidator(validators.MinLengthValidator):
	message = 'Ensure this value has at least %(limit_value)d elements (it has %(show_value)d).'

class MaxLengthValidator(validators.MaxLengthValidator):
	message = 'Ensure this value has at most %(limit_value)d elements (it has %(show_value)d).'

class CommaSeparatedCharField(forms.Field):
	def __init__(self, dedup=True, max_length=None, min_length=None, *args, **kwargs):
		self.dedup = dedup
		self.max_length = max_length
		self.min_length = min_length
		super(CommaSeparatedCharField, self).__init__(*args, **kwargs)
		if min_length is not None:
			self.validators.append(MinLengthValidator(min_length))
		if max_length is not None:
			self.validators.append(MaxLengthValidator(max_length))

	def to_python(self, value):
		if value in validators.EMPTY_VALUES:
			return []

		value = [item.strip() for item in re.split(r'[,;]+', value) if item.strip()]
		if self.dedup:
			value = list(set(value))

		return value

	def clean(self, value):
		value = self.to_python(value)
		self.validate(value)
		self.run_validators(value)
		return value

class LabelledHiddenWidget(forms.HiddenInput):
	def __init__(self, *args, **kwargs):
		super(LabelledHiddenWidget, self).__init__(*args, **kwargs)

	@property
	def is_hidden(self):
		return False

	def render(self, name, value, attrs=None, renderer=None):
		input_html = super(LabelledHiddenWidget, self).render(name,
				value, attrs=attrs, renderer=renderer)
		for pk, val in self.choices:
			if pk == value:
				input_html += val
				break
		return input_html
