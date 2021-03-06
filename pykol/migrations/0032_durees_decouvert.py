# Generated by Django 2.1 on 2019-05-22 13:08

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0031_contraintes_comptabilite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='compte',
            name='decouvert_autorise',
            field=models.BooleanField(default=False, help_text="Ce champ indique si le compte peut être à découvert. Dans ce cas, on peut limiter le nombre d'heures du découvert en donnant des valeurs explicites aux durées à découvert autorisées.", verbose_name='découvert autorisé'),
        ),
        migrations.AlterField(
            model_name='compte',
            name='decouvert_duree',
            field=models.DurationField(blank=True, default=datetime.timedelta, help_text="Lorsque le découvert est autorisé sur ce compte, ce champ donne une limite sur le nombre d'heures comptabilisées négativement. Par exemple, si ce champ vaut 3h, le solde du compte devra toujours être supérieur ou égal à -3h.", null=True, verbose_name='durée à découvert autorisée'),
        ),
        migrations.AlterField(
            model_name='compte',
            name='decouvert_duree_interrogation',
            field=models.DurationField(blank=True, default=datetime.timedelta, null=True, verbose_name="durée d'interrogation à découvert autorisée"),
        ),
    ]
