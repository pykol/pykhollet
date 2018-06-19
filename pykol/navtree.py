# -*- coding: utf-8 -*-

from django.urls import reverse

from pykol.navigation import item

navtree = (
		item(name="home",
			label="Tableau de bord",
			url=reverse("home"),
			icon="bar-chart",
			),
		)
