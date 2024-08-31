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

import copy
from importlib import import_module
from django.urls import reverse

class NavigationChildrenList:
	def __init__(self, children_list):
		self.children_list = children_list

	def __len__(self):
		return len(self.children_list)

	def append(self, x):
		self.children_list.append(x)

	def __call__(self, user):
		return NavigationChildrenListUser(self.children_list, user)

class NavigationChildrenListUser:
	def __init__(self, children_list, user):
		self.children_list = children_list
		self.user = user

	def __iter__(self):
		for child in self.children_list:
			if child.is_allowed(self.user):
				yield(child.get_for_user(self.user))

class NavigationItem:
	"""
	Une entrée dans le menu de navigation
	"""
	def __init__(self, label, url=None, absolute_url=None, priority=0,
			permissions=[], icon=None, name=None, parent=None,
			children=[], user_passes_test=None):
		self.label = label
		self.url = url
		self.url_args = []
		self.absolute_url = absolute_url
		self.priority = priority
		self.permissions = permissions
		self.user_passes_test = user_passes_test
		self.icon = icon
		self.name = name
		self.children = NavigationChildrenList(children)
		self.parent = None

	def is_link(self):
		return self.url is not None or self.absolute_url is not None

	def get_link(self):
		if self.absolute_url is not None:
			return self.absolute_url
		if self.url is not None:
			return reverse(self.url, args=self.url_args)

	def __iter__(self):
		return iter(self.children)

	def is_allowed(self, user):
		if callable(self.user_passes_test):
			if not self.user_passes_test(user):
				return False
		return user.has_perms(self.permissions)

	def is_current(self, request):
		return request.path_info == self.url

	def has_children(self):
		return len(self.children) > 0

	def get_for_user(self, user):
		return NavigationItemUser(self, user)

class NavigationItemUser(NavigationItem):
	def __new__(cls, navitem, user):
		instance = copy.copy(navitem)
		instance.__class__ = cls
		return instance

	def __init__(self, _, user):
		self.user = user

	def __iter__(self):
		return iter(self.children(self.user))

class MesClassesChildren:
	def __call__(self, user):
		def iter_classes():
			for classe in user.mes_classes().order_by('nom'):
				yield NavigationItem(
						label=str(classe),
						name="classe-{}".format(classe.slug),
						absolute_url=classe.get_absolute_url(),
						icon='users')
		return iter_classes()

	def __len__(self):
		return 42

class Navigation:
	"""
	Menu de navigation complet
	"""
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

	def get_for_user(self, user):
		return self.root_item.get_for_user(user)

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
		children = []

	item = NavigationItem(children=children, **kwargs)

	return item

def include(navtree_module):
	if isinstance(what, six.string_types):
		navtree_module = import_module(navtree_module)
	tree_items = getattr(navtree_module, 'navtree')

	return tree_items

def build_nav(name="main"):
	nav = Navigation._all_navigation[name]
