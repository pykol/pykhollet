# -*- coding: utf-8 -*-
"""
Grosse migration qui initialise les données de comptabilité avec celles
des modèles existants.

Cette migration crée toute la hiérarchie de comptes et l'attache aux
modèles déjà existants dans pyKol. Elle tente de réinventer à postériori
tous les mouvements de comptes à partir des colloscopes et des relevés
d'heures, comme s'ils avaient été créés directement.
"""

from django.db import migrations, models

from datetime import timedelta

# Constantes provenant du modèle Compte, puisqu'elles sont inaccessibles
# au travers du modèle lui-même durant la migration.
COMPTE_CATEGORIE_DEPENSES = 0
COMPTE_CATEGORIE_ACTIFS = 1
COMPTE_CATEGORIE_REVENUS = 2
COMPTE_CATEGORIE_DETTES = 3
COMPTE_CATEGORIE_FONDS_PROPRES = 4

# Constantes provenant du modèle Colle.
COLLE_ETAT_BROUILLON = 5
COLLE_ETAT_PREVUE = 0
COLLE_ETAT_NOTEE = 1
COLLE_ETAT_EFFECTUEE = 4
COLLE_ETAT_RELEVEE = 2
COLLE_ETAT_ANNULEE = 3

COLLE_MODE_INTERROGATION = 0
COLLE_MODE_TD = 1

# Constantes provenant du modèle Mouvement
MOUVEMENT_ETAT_BROUILLON = 0
MOUVEMENT_ETAT_VALIDE = 1

# Constantes provenant du modèle ColleReleveLigne
COLLERELEVELIGNE_ETAT_NOUVEAU = 0
COLLERELEVELIGNE_ETAT_PAYE = 1
COLLERELEVELIGNE_ETAT_SAISIE_ASIE = 2

# Constantes provenant du modèle Classe
CLASSE_NIVEAU_PREMIERE_ANNEE = 1
CLASSE_NIVEAU_DEUXIEME_ANNEE = 2

# Constantes provenant du modèle abstrait ColleDureeTaux
TAUX_1A_INF20 = 1
TAUX_1A_INF35 = 2
TAUX_1A_SUP36 = 3
TAUX_2A_INF20 = 4
TAUX_2A_INF35 = 5
TAUX_2A_SUP36 = 6

def creation_compte(apps, **kwargs):
	Compte = apps.get_model('pykol', 'Compte')
	compte = Compte(**kwargs)
	# Création à la main de valeurs farfelues pour la hiérarchie MPTT
	compte.lft = 0
	compte.rght = 0
	compte.level = 0
	compte.tree_id = 0

	compte.save()
	return compte

def cree_comptes_rectorats(apps, schema_editor):
	"""
	Création des comptes de dotation et de paiement de chaque rectorat
	"""
	Academie = apps.get_model('pykol', 'Academie')

	racine_rectorats = creation_compte(apps, categorie=COMPTE_CATEGORIE_REVENUS,
		nom="Rectorats")
	racine_rectorats.save()

	racine_asie = creation_compte(apps, categorie=COMPTE_CATEGORIE_DEPENSES,
		nom="Paiements")
	racine_asie.save()

	for academie in Academie.objects.all():
		academie.compte_dotation = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_REVENUS,
			nom=academie.nom_complet,
			parent=racine_rectorats)

		academie.compte_paiement = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_DEPENSES,
			nom=academie.nom_complet,
			parent=racine_asie)

		academie.compte_dotation.save()
		academie.compte_paiement.save()
		academie.save()

def reverse_cree_comptes_rectorats(apps, schema_editor):
	"""
	Suppression des compte_dotation et des compte_paiement des
	académies. On supprime aussi les comptes racines des rectorats.
	"""
	Compte = apps.get_model('pykol', 'Compte')
	#TODO ancêtres
	Compte.objects.filter(
		models.Q(rectorat__isnull=False) |
		models.Q(asie__isnull=False)
		).delete()

def cree_comptes_etablissements(apps, schema_editor):
	"""
	Création des comptes pour les établissements.
	"""
	Etablissement = apps.get_model('pykol', 'Etablissement')

	racine_etab = creation_compte(apps, categorie=COMPTE_CATEGORIE_ACTIFS,
		nom="Établissements")
	racine_etab.save()

	for etablissement in Etablissement.objects.filter(
			classe__isnull=False).distinct():
		compte_etab = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom=etablissement.appellation,
			parent=racine_etab)
		compte_etab.save()

		etablissement.compte_colles = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="Dotation",
			parent=compte_etab)
		etablissement.compte_colles.save()

		etablissement.compte_releves = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="Relevés",
			parent=compte_etab)
		etablissement.compte_releves.save()

		etablissement.save()

def reverse_cree_comptes_etablissements(apps, schema_editor):
	"""
	Suppression des comptes des établissements.
	"""
	Compte = apps.get_model('pykol', 'Compte')
	# TODO ancêtres
	Compte.objects.filter(
		models.Q(etablissement_dotation__isnull=False) |
		models.Q(etablissement_releves__isnull=False)
		).delete()

def cree_comptes_classes(apps, schema_editor):
	"""
	Création des comptes de dotation en heures pour chaque classe.

	Ces comptes sont placés sous une racine unique qui regroupe toutes
	les classes de l'établissement.
	"""
	Classe = apps.get_model('pykol', 'Classe')

	for classe in Classe.all_objects.all():
		classe.compte_colles = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="{classe} - {annee}".format(classe=classe.nom,
				annee=classe.annee.nom),
			parent=classe.etablissement.compte_colles)

		classe.compte_colles.save()
		classe.save()


def reverse_cree_comptes_classes(apps, schema_editor):
	"""
	Suppression des comptes des classes.
	"""
	Compte = apps.get_model('pykol', 'Compte')
	Compte.objects.filter(classe__isnull=False).delete()

def str_collesenseignement(cens):
	if cens.nom:
		return cens.nom
	else:
		matiere = cens.enseignements.first().matiere
		while matiere.parent:
			matiere = matiere.parent
		return matiere.nom

def cree_comptes_enseignements(apps, schema_editor):
	"""
	Création d'un compte de dotation en heure pour chaque groupe
	d'enseignements dotés en colles.
	"""
	CollesEnseignement = apps.get_model('pykol', 'CollesEnseignement')

	for cens in CollesEnseignement.objects.all():
		cens.compte_colles = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom=str_collesenseignement(cens),
			parent=cens.classe.compte_colles)
		cens.compte_colles.save()
		cens.save()
		# TODO créer des sous-comptes pour chaque enseignement ?

def reverse_cree_comptes_enseignements(apps, schema_editor):
	"""
	Suppression des comptes des objets ColleEnseignement.
	"""
	Compte = apps.get_model('pykol', 'Compte')
	Compte.objects.filter(collesenseignement__isnull=False
		).delete()

def cree_comptes_professeurs(apps, schema_editor):
	"""
	Création des comptes d'heures prévues et d'heures effectuées pour
	tous les professeurs.
	"""
	Professeur = apps.get_model('pykol', 'Professeur')

	racine_profs = creation_compte(apps, categorie=COMPTE_CATEGORIE_ACTIFS,
		nom="Professeurs")
	racine_profs.save()

	for prof in Professeur.objects.all():
		compte_prof = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="{0.last_name} {0.first_name}".format(prof),
			parent=racine_profs,
			proprietaire=prof)
		compte_prof.save()

		prof.compte_prevu = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="Colles prévues",
			parent=compte_prof,
			proprietaire=prof)
		prof.compte_prevu.save()

		prof.compte_effectue = creation_compte(apps,
			categorie=COMPTE_CATEGORIE_ACTIFS,
			nom="Colles effectuées",
			parent=compte_prof,
			proprietaire=prof)
		prof.compte_effectue.save()

		prof.save()

def reverse_cree_comptes_professeurs(apps, schema_editor):
	"""
	Suppression des comptes associés aux professeurs.
	"""
	Compte = apps.get_model('pykol', 'Compte')
	# TODO ancêtres
	Compte.objects.filter(
		models.Q(professeur_prevues__isnull=False) |
		models.Q(professeur_effectue__isnull=False)
		).delete()

def colle_details(colle):
	return colle.colledetails_set.get(actif=True)

def colle_duree_interrogation(colle):
	if colle.mode == COLLE_MODE_TD:
		return colle.duree
	else:
		if colle.colles_ens.frequence == 1: # FREQUENCE_HEBDOMADAIRE
			par_eleve = timedelta(minutes=20)
		else:
			par_eleve = colle.colles_ens.duree_frequentielle

		return len(colle_details(colle).eleves.all()) * par_eleve

def mouvement_virement(apps, compte_debit, compte_credit,
		duree, duree_interrogation=None,
		taux=None, **kwargs):
	Mouvement = apps.get_model('pykol', 'Mouvement')
	MouvementLigne = apps.get_model('pykol', 'MouvementLigne')
	mv = Mouvement(**kwargs)
	mv.save()

	# Ligne de débit
	MouvementLigne(
		compte=compte_debit,
		mouvement=mv,
		duree=-duree,
		duree_interrogation=-duree_interrogation,
		taux=taux,
		motif=mv.motif).save()

	# Ligne de crédit
	MouvementLigne(
		compte=compte_credit,
		mouvement=mv,
		duree=duree,
		duree_interrogation=duree_interrogation,
		taux=taux,
		motif=mv.motif).save()

	return mv

def mouvement_virement_retour(apps, self):
	Mouvement = apps.get_model('pykol', 'Mouvement')
	mv = Mouvement(annee=self.annee,
		motif="Annulation du mouvement {pk}".format(pk=self.pk))
	mv.save()

	for ligne in self.lignes.all():
		# Ceci provoque la création d'une nouvelle instance lors de
		# la sauvegarde.
		ligne.pk = None
		ligne.duree = -ligne.duree
		ligne.duree_interrogation = -ligne.duree_interrogation
		ligne.mouvement = mv
		ligne.save()

	return mv

def comptabilite_colloscopes(apps, schema_editor):
	"""
	Ajout des mouvements de comptes pour les colles prévues et les
	colles effectuées.
	"""
	Colle = apps.get_model('pykol', 'Colle')
	Mouvement = apps.get_model('pykol', 'Mouvement')
	MouvementLigne = apps.get_model('pykol', 'MouvementLigne')

	for colle in Colle.all_objects.all():
		# On ajoute un premier mouvement correspondant à la création de
		# la colle. Ce mouvement débite la dotation de la classe.
		if colle.etat == COLLE_ETAT_BROUILLON:
			etat = MOUVEMENT_ETAT_BROUILLON
		else:
			etat = MOUVEMENT_ETAT_VALIDE

		mv = mouvement_virement(apps,
			compte_debit=colle.colles_ens.compte_colles,
			compte_credit=colle_details(colle).colleur.compte_prevu,
			duree=colle.duree,
			duree_interrogation=colle_duree_interrogation(colle),
			annee=colle.classe.annee,
			motif="Ajout au colloscope en {classe} de la colle du {date}".format(
				classe=colle.classe.nom,
				date=colle_details(colle).horaire),
			colle=colle,
			etat=etat)

		# Si la colle est annulée, on crée le mouvement inverse pour
		# rendre la dotation à la classe.
		if colle.etat == COLLE_ETAT_ANNULEE:
			mouvement_virement_retour(apps, mv)

		# Si la colle est notée, effectuée ou relevée, on transfère les
		# heures au compte d'heures effectuées par le professeur. Les
		# heures relevées seront transférées plus tard par la fonction
		# migrer_releves vers le compte d'heures du relevé.
		if colle.etat in (COLLE_ETAT_NOTEE, COLLE_ETAT_EFFECTUEE,
				COLLE_ETAT_RELEVEE):
			mouvement_virement(apps,
				compte_debit=colle_details(colle).colleur.compte_prevu,
				compte_credit=colle_details(colle).colleur.compte_effectue,
				duree=colle.duree,
				duree_interrogation=colle_duree_interrogation(colle),
				annee=colle.classe.annee,
				motif="Colle du {date} en {classe} effectuée".format(
					classe=colle.classe.nom,
					date=colle_details(colle).horaire),
				colle=colle,
				etat=MOUVEMENT_ETAT_VALIDE)

def reverse_comptabilite_colloscopes(apps, schema_editor):
	"""
	Suppression des mouvements de comptes provenant de colles.
	"""
	Mouvement = apps.get_model('pykol', 'Mouvement')
	Mouvement.objects.filter(colle__isnull=False).delete()

def taux_colle(classe):
	if classe.etudiants.all():
		effectif = classe.etudiants.sur_ventilation_service(classe.annee).count()
	else:
		effectif = classe.effectif_sts or 0

	if classe.niveau == CLASSE_NIVEAU_PREMIERE_ANNEE:
		if effectif <= 20:
			return TAUX_1A_INF20
		elif effectif <= 35:
			return TAUX_1A_INF35
		else:
			return TAUX_1A_SUP36
	else:
		if effectif <= 20:
			return TAUX_2A_INF20
		elif effectif <= 35:
			return TAUX_2A_INF35
		else:
			return TAUX_2A_SUP36

def migrer_releves(apps, schema_editor):
	"""
	Ajout d'un compte par relevé et des mouvements de comptes
	correspondant au relevé et au paiement des heures de colles.
	"""
	ColleReleve = apps.get_model('pykol', 'ColleReleve')
	ColleReleveLigne = apps.get_model('pykol', 'ColleReleveLigne')
	Mouvement = apps.get_model('pykol', 'Mouvement')
	MouvementLigne = apps.get_model('pykol', 'MouvementLigne')
	Colle = apps.get_model('pykol', 'Colle')

	# Création d'un compte spécifique pour chaque relevé d'heures
	for releve in ColleReleve.objects.all():
		releve.compte_colles = creation_compte(apps,
				categorie=COMPTE_CATEGORIE_ACTIFS,
				nom="Relevé du {date}".format(date=releve.date),
				parent=releve.etablissement.compte_releves)
		releve.compte_colles.save()
		releve.save()

	# Création des mouvements comptables correspondant au paiement des
	# colles.
	for ligne_releve in ColleReleveLigne.objects.all():
		# On crée d'abord le mouvement pour la relève des colles
		mv = Mouvement(
			annee=ligne_releve.releve.annee,
			motif="Relevé du {date}".format(date=ligne_releve.releve.date),
			etat=MOUVEMENT_ETAT_VALIDE)
		mv.save()
		ligne_releve.mouvement = mv
		ligne_releve.save()

		# Ajout de la ligne de crédit vers le compte du relevé
		ligne_credit = MouvementLigne(
			compte=ligne_releve.releve.compte_colles,
			mouvement=mv,
			duree=ligne_releve.duree,
			duree_interrogation=ligne_releve.duree_interrogation,
			taux=ligne_releve.taux)
		ligne_credit.save()

		# Si la ligne du relevé est payée, on crée également les
		# mouvement correspondant au paiement de ces lignes.
		if ligne_releve.etat == COLLERELEVELIGNE_ETAT_PAYE:
			mouvement_virement(apps,
				compte_debit=ligne_releve.releve.compte_colles,
				compte_credit=ligne_releve.releve.etablissement.academie.compte_paiement,
				annee=ligne_releve.releve.annee,
				motif="Paiement du relevé du {releve}".format(releve=ligne_releve.releve.date),
				duree=ligne_releve.duree,
				duree_interrogation=ligne_releve.duree_interrogation,
				taux=ligne_releve.taux,
				etat=MOUVEMENT_ETAT_VALIDE,
				)
		# TODO lettrer les lignes de relevé avec les lignes de paiement
	
	# Création des lignes de débit des colles relevées
	for colle in Colle.all_objects.filter(releve__isnull=False):
		colleur = colle_details(colle).colleur
		taux = taux_colle(colle.classe)
		ligne = colle.releve.lignes.filter(colleur=colleur,
				taux=taux).first()

		if colle.mode == COLLE_MODE_INTERROGATION:
			# Le "or" est là parce que certains colleurs ont réussi à
			# déclarer des colles, qui sont en fait des TD, sans mettre
			# de note.
			duree_interrogation = colle.collenote_set.aggregate(
					duree_interrogation=models.Sum('duree')
				)['duree_interrogation'] or colle.duree
		else:
			duree_interrogation = colle.duree

		MouvementLigne(
			compte=colleur.compte_effectue,
			mouvement=ligne.mouvement,
			duree=-colle.duree,
			duree_interrogation=-duree_interrogation,
			taux=taux).save()

def reverse_migrer_releves(apps, schema_editor):
	"""
	Suppression des mouvements de comptes provenant de relevés.
	"""
	Mouvement = apps.get_model('pykol', 'Mouvement')
	Mouvement.objects.filter(collereleveligne__isnull=False).delete()


class Migration(migrations.Migration):

	dependencies = [
		('pykol', '0025_integration_comptabilite'),
	]

	operations = [
		migrations.RunPython(cree_comptes_rectorats, reverse_cree_comptes_rectorats),
		migrations.RunPython(cree_comptes_etablissements, reverse_cree_comptes_etablissements),
		migrations.RunPython(cree_comptes_classes, reverse_cree_comptes_classes),
		migrations.RunPython(cree_comptes_enseignements, reverse_cree_comptes_enseignements),
		migrations.RunPython(cree_comptes_professeurs, reverse_cree_comptes_professeurs),
		migrations.RunPython(comptabilite_colloscopes, reverse_comptabilite_colloscopes),
		migrations.RunPython(migrer_releves, reverse_migrer_releves),
	]
