from django.conf.urls import url, include

from . import views

colles_urlpatterns = [
	url(r'^$', views.colloscope_home, name='colloscope_home'),
	url(r'(?P<slug>[\w-]+)/$', views.colloscope, name='colloscope'),
	url(r'(?P<slug>[\w-]+)/trinomes$', views.trinomes, name='trinomes'),
	url(r'(?P<slug>[\w-]+)/semaines$', views.semaines, name='semaines'),
]

urlpatterns = [
	url(r'^$', views.home, name='home'),
	url(r'^', include('django.contrib.auth.urls')),
	url(r'^colles/', include(colles_urlpatterns)),
]
