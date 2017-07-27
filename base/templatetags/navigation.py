# -*- coding: utf-8 -*-

from django import template
register = template.Library()

from base.navigation import nav

@register.inclusion_tag('navigation.html')
def show_navigation(nav=nav):
	return {'navigation': nav}
