Installation de pyKol
=====================

Avant de commencer à installer ce programme, souvenez-vous qu'il est
distribué sous licence GNU Affero GPL version 3. Si vous apportez des
modifications, vous devez fournir un moyen à vos utilisateurs d'en
obtenir les sources. Toute proposition d'amélioration est la bienvenue,
n'hésitez pas à contacter les auteurs.

Répertoires de travail
----------------------

Nous aurons besoin de deux répertoires pour stocker les
différentes parties :
* un répertoire $PYKOL_VENV qui accueillera l'environnement virtuel
  Python pour faire tourner pyKol ;
* un répertoire $MON_PYKOL dans lequel vous personnaliserez votre
  instance de pyKol, en plaçant les sources de l'application dans le
  sous-répertoire pykol.

Vous pouvez par exemple choisir :
```bash
PYKOL_VENV=~/.local/virtualenvs/pykol
MON_PYKOL=~/mon_pykol
PYKOL_DIR=$MON_PYKOL/pykol
```

Initialisation de l'environnement virtuel Python 3
--------------------------------------------------

Créez un environnement virtuel Python 3 :
```bash
virtualenv -p python3 $PYKOL_VENV
```
Activez cet environnement virtuel pour toute la suite de
l'installation :
```bash
source $PYKOL_VENV/bin/activate
```

Création de votre projet
------------------------

Installez Django dans l'environnement virtuel :
```bash
pip install django
```

pyKol est une application Django. Chaque installation pour un
établissement correspond à un projet Django, dans lequel vous installez
l'application pyKol. Choisissez un nom de projet pour désigner votre
instance de pyKol et créez ce projet :
```bash
cd $MON_PYKOL/../
django-admin startproject $(basename $MON_PYKOL)
```
Vous disposez alors d'un projet Django vierge dans le répertoire
$MON_PYKOL.

Téléchargement du code source de pyKol
--------------------------------------

```bash
git clone https://github.com/pykol/pykol $PYKOL_DIR
```

Modifiez ensuite le fichier $MON_PYKOL/mon_pykol/settings.py afin
d'ajouter l'application pykol en tête des applications installées pour
ce projet, et placer quelques réglages concernant l'identification :
```python
# Application definition
INSTALLED_APPS = [
  'pykol',
  ...
]

AUTH_USER_MODEL='pykol.User'

# Gestion des permissions
AUTHENTICATION_BACKENDS = [
	'pykol.lib.auth.PykolBackend',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
```

Enfin, réglez le fichier d'URL $MON_PYKOL/mon_pykol/urls.py de votre projet afin qu'il inclue les
URLs de l'application pyKol. Si vous souhaitez installer pyKol à la
racine du site, le contenu suivant devrait faire l'affaire :
```python
from pykol.admin import admin_site

urlpatterns = [
	path('admin/', admin_site.urls),
	path('', include('pykol.urls')),
]
```

Installation des dépendances
----------------------------

```bash
pip install -r $PYKOL_DIR/requirements.txt
```

Initialisation de la base de données
------------------------------------

Configurez le moteur de base de données que vous souhaitez en modifiant
les réglages dans le fichier $MON_PYKOL/mon_pykol/settings.py.

Pour des tests, la base de données SQLite3 créée par défaut par
django-admin peut suffire (cela risque cependant d'être rapidement assez
lent, par exemple lors de l'import des données depuis les fichiers
SIECLE et STS). pyKol n'a été véritablement testé qu'avec PostgreSQL.

Une fois votre base de données correctement configurée, chargez les
données initiales :

```bash
python $MON_PYKOL/manage.py migrate
python $MON_PYKOL/manage.py loaddata academies.json etablissements.json
```

Créez un premier super-utilisateur :
```bash
$PYKOL_VENV/bin/python $MON_PYKOL/manage.py createsuperuser
```

Lancement du serveur de tests
-----------------------------

Vous pouvez alors lancer le serveur de tests et vous connecter avec le
compte super-utilisateur que vous venez de créer :
```bash
$PYKOL_VENV/bin/python $MON_PYKOL/manage.py runserver
```

Avec ce compte, vous pouvez accéder à la page d'import des données
SIECLE et STS depuis le menu Paramétrage. Toutes les données sont
attachées à une année scolaire. L'import d'un fichier STS créera
automatiquement l'année scolaire correspondante. Si vous ne disposez pas
d'export STS, utilisez l'interface d'administration de Django pour créer
manuellement les données dont vous avez besoin.
