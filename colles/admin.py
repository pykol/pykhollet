# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from base.admin import admin_site
from .models import Semaine, Creneau, Colle

admin_site.register(Semaine)
admin_site.register(Creneau)
admin_site.register(Colle)
