# -*- coding: utf-8

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from base.models import Classe

@login_required
def colloscope_home(request):
	return render(request, 'base.html')

@login_required
def colloscope(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	return render(request, 'base.html')

@login_required
def trinomes(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	return render(request, 'base.html')

@login_required
def create_trinome(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	return render(request, 'base.html')



from base.navigation import nav
nav.register("Colloscope", "colloscope", icon="calendar")
