# -*- coding: utf-8

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def colloscope(request):
	return render(request, 'base.html')

from base.navigation import nav
nav.register("Colloscope", "colloscope", icon="calendar")
