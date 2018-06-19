from django.conf.urls import url
from django.urls import path, include

from . import views

colles_urlpatterns = [
	path('', views.colloscope_home, name='colloscope_home'),
	path('<slug:slug>/', views.colloscope, views.colloscope, name='colloscope'),
	path('<slug:slug>/trinomes$', views.trinomes, name='trinomes'),
	path('<slug:slug>/semaines$', views.semaines, name='semaines'),
]

urlpatterns = [
	path('', views.home, name='home'),
    path(r'accounts/', include('django.contrib.auth.urls')),
	path('colles/', include(colles_urlpatterns)),
]
