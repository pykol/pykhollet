# -*- coding: utf-8

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
	return render(request, 'base.html')

