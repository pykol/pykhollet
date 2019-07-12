# Generated by Django 2.2.1 on 2019-07-12 10:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0036_compte_champs_mptt'),
    ]

    operations = [
        migrations.AddField(
            model_name='colle',
            name='ligne_dotation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pykol.MouvementLigne', verbose_name='ligne de dotation'),
        ),
    ]
