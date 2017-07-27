# -*- coding: utf-8 -*-

class NavigationItem:
	def __init__(self, label, url, priority, permissions, icon=None):
		self.label = label
		self.url = url
		self.priority = priority
		self.permissions = permissions
		self.icon = icon
		self.is_active = False

	def is_allowed(self, request):
		return request.user.has_perms(self.permissions)

class Navigation:
	def __init__(self, name="main"):
		self.items = []
		self.name = name

	def register(self, label, url, priority=10, permissions=None, icon=None):
		self.items.append(NavigationItem(label, url, priority,
			permissions, icon))

	def __iter__(self):
		return iter(self.items)

	def iter_allowed(self, request):
		for item in self.items:
			if item.is_allowed(request):
				yield(item)

nav = Navigation()
