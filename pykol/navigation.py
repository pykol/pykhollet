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

from importlib import import_module
from django.utils import six

class NavigationItem:
	def __init__(self, label, url=None, priority=0, permissions=None,
			icon=None, name=None, parent=None, children=[]):
		self.label = label
		self.url = url
		self.priority = priority
		self.permissions = permissions
		self.icon = icon
		self.name = name
		self.children = []
		self.parent = None

	def __iter__(self):
		return iter(self.children)

	def is_allowed(self, request):
		return request.user.has_perms(self.permissions)

	def is_current(self, request):
		return request.path_info == self.url

	def has_children(self):
		return len(self.children) > 0

class Navigation:
	_all_navigation = {}

	def __init__(self, name="main"):
		if name in Navigation._all_navigation:
			raise ValueError("Trying to create twice a Navigation "
					"called %(name)s" % {'name': name})
		Navigation._all_navigation[name] = self

		self.root_item = NavigationItem(label=None, url=None,
				priority=0, permissions=None, icon=None,
				name="root")
		self.named_items = {'root': self.root_item}
		self.name = name

	def register(self, item):
		if item.name is not None:
			self.named_items[item.name] = item

		if item.parent is None:
			self.root_item.children.append(item)
		else:
			self.named_items[item.parent].children.append(item)

	def __iter__(self):
		return iter(self.root_item)

	def iter_allowed(self, request):
		for item in self.root_item:
			if item.is_allowed(request):
				yield(item)

nav = Navigation()

def tuple_flatten(tpl):
	res = []
	for elt in tpl:
		if isinstance(elt, tuple) or isinstance(elt, list):
			res += elt
		else:
			res.append(elt)
	return tuple(res)

def item(**kwargs):
	try:
		children = tuple_flatten(kwargs.pop('children'))
	except KeyError:
		children = None

	item = NavigationItem(children=children, **kwargs)

	return item

def include(navtree_module):
	if isinstance(what, six.string_types):
		navtree_module = import_module(navtree_module)
	tree_items = getattr(navtree_module, 'navtree')

	return tree_items

def build_nav(name="main"):
	nav = Navigation._all_navigation[name]
