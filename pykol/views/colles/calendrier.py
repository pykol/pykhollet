# -*- coding: utf-8 -*-

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018 Florian Hatat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from zoneinfo import ZoneInfo
import vobject

from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from pykol.models.base import Etudiant
from pykol.models.colles import Colle
from pykol.models.base import JetonAcces

def calendrier(request, uuid):
	jeton = get_object_or_404(JetonAcces, uuid=uuid, scope='colles_icalendar')
	utilisateur = jeton.owner

	cal = vobject.iCalendar()
	utc_zone = ZoneInfo('UTC')

	if hasattr(jeton.owner, 'professeur'):
		colles = Colle.objects.filter(colledetails__actif=True,
			colledetails__colleur=utilisateur)
		professeur = True
	elif hasattr(jeton.owner, 'etudiant'):
		colles = Colle.objects.filter(colledetails__actif=True,
			colledetails__eleves=utilisateur)
		professeur = False
	else:
		colles = Colle.objects.none()
		professeur = False

	for colle in colles:
		vevent = cal.add('vevent')
		vevent.add('uid').value = 'colle-{pk}@{host}'.format(
				pk=colle.pk, host=request.get_host())

		if professeur:
			vevent.add('summary').value = \
				"Colle en {classe}".format(classe=colle.classe)
		else:
			vevent.add('summary').value = \
				"Colle de {matiere}".format(matiere=colle.matiere)

		vevent.add('dtstart').value = colle.details.horaire.astimezone(utc_zone)
		vevent.add('dtend').value   = (colle.details.horaire + colle.duree).astimezone(utc_zone)
		vevent.add('location').value = colle.details.salle
		if colle.etat == Colle.ETAT_BROUILLON:
			vevent.add('status').value = 'TENTATIVE'
		elif colle.etat == Colle.ETAT_ANNULEE:
			vevent.add('status').value = 'CANCELLED'
		else:
			vevent.add('status').value = 'CONFIRMED'

		prof_att = vevent.add('attendee')
		prof_att.role_param = 'CHAIR'

		if professeur:
			prof_att.cn_param = str(colle.colleur)
		else:
			prof_att.cn_param = str(colle.colleur.short_name_civilite())

		prof_att.value = 'MAILTO:{email}'.format(email=colle.colleur.email)
		prof_att.partstat_param = 'ACCEPTED'

		for etudiant in colle.details.eleves.all():
			att = vevent.add('attendee')
			att.role_param = 'REQ-PARTICIPANT'
			att.cn_param = str(etudiant)
			att.partstat_param = 'ACCEPTED'
			if etudiant.email:
				att.value = 'MAILTO:{email}'.format(email=etudiant.email)
			else:
				att.value = request.build_absolute_uri(etudiant.get_absolute_url())

	response = HttpResponse(cal.serialize(),
			content_type='text/calendar')
	response['Content-Disposition'] = 'attachment; filename="planning.ics"'
	return response
