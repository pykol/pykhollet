# Generated by Django 2.1 on 2019-04-18 12:03

from django.db import migrations, models
import pykol.lib.files


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0026_mention_ligne_facultative'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etablissement',
            name='tampon_etablissement',
            field=models.ImageField(blank=True, null=True, storage=pykol.lib.files.PrivateFileSystemStorage(), upload_to='tampon_etablissement/', verbose_name="tampon de l'établissement"),
        ),
        migrations.AlterField(
            model_name='user',
            name='signature',
            field=models.ImageField(blank=True, null=True, storage=pykol.lib.files.PrivateFileSystemStorage(), upload_to='signature/'),
        ),
    ]
