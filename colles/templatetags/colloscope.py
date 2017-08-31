# -*- coding: utf-8 -*-

from django import template
register = template.Library()

@register.filter(expects_localtime=True)
def heure_pour_colloscope(value):
	if value.minute == 0:
		return "{:%H}".format(value)
	else:
		return "{:%H-%M}".format(value)
