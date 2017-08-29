# -*- coding: utf-8 -*-

class NavigationItem:
	def __init__(self, label, url, priority, permissions, icon=None,
			name=None):
		self.label = label
		self.url = url
		self.priority = priority
		self.permissions = permissions
		self.icon = icon
		self.is_active = False
		self.name = name
		self.items = []

	def __iter__(self):
		return iter(self.items)

	def is_allowed(self, request):
		return request.user.has_perms(self.permissions)

	def has_children(self):
		return len(self.items) > 0

class Navigation:
	def __init__(self, name="main"):
		self.root_item = NavigationItem(label=None, url=None,
				priority=0, permissions=None, icon=None,
				name="root")
		self.named_items = {'root': self.root_item}
		self.name = name

	def register(self, label, url, priority=10, permissions=None,
			icon=None, name=None, parent=None):

		item = NavigationItem(label, url, priority, permissions, icon, name)

		if name is not None:
			self.named_items[name] = item

		if parent is None:
			self.root_item.items.append(item)
		else:
			self.named_items[parent].items.append(item)

	def __iter__(self):
		return iter(self.root_item)

	def iter_allowed(self, request):
		for item in self.root_item:
			if item.is_allowed(request):
				yield(item)

nav = Navigation()
