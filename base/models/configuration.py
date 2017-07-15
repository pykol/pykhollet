# -*- coding:utf8 -*-
from django.db import models

from etablissement import Etablissement

class Configuration(models.Model):
	etablissement = models.ForeignKey(Etablissement)
