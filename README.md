pyKol - Un gestionnaire de colles en CPGE écrit avec Python et Django
=====================================================================

pyKol est un logiciel qui aide au suivi des heures de colles effectuées
dans les classes de CPGE. Il permet :
- aux colleurs de déclarer les heures effectuées et de suivre l'état de
leur paiement heure par heure ;
- aux professeurs d'obtenir les notes de colles données par leurs
colleurs ;
- à l'administration d'obtenir les décomptes d'heures effectuées afin de
les mettre en paiement. Les informations sur les heures à payer sont
présentées de la manière dont il faut les saisir dans ASIE.

pyKol est capable d'importer les données concernant les classes et les
professeurs depuis les exports XML standard des applications de
l'Éducation nationale (SIECLE pour la base élèves, les nomenclatures et
les structures, STS pour les professeurs et leurs services dans les
classes). L'initialisation des données en début d'année scolaire se fait
ainsi en quelques instants, en limitant le plus possible la saisie
manuelle de données par l'administrateur.

Il permet de suivre les enveloppes d'heures de colles :
- suivi des volumes d'heures déléguées par le rectorat ;
- suivi des heures consommées ;
- saisie d'une répartition des heures globales en fléchant des heures
sur chaque classe, afin de vérifier que les colloscopes respectent les
dotations.

pyKol enregistre le planning annuel des colles, saisi (ou importé depuis
un tableur) par le responsable du colloscope de chaque classe. Les
colleurs en se connectant accèdent ainsi directement à leur planning
(colles à noter et colles à venir). Pour chaque colle à noter, la liste
des étudiants est préremplie.

Ce programme est distribué sous licence GNU Affero GPL version 3.
