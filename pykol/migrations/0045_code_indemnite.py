# Generated by Django 2.2.5 on 2019-11-05 20:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0044_colle_ligne_dotation_nulle'),
    ]

    operations = [
        migrations.AddField(
            model_name='collereleveligne',
            name='code_indemnite',
            field=models.CharField(choices=[('0207', 'professeur en CPGE'), ('2249', "moins d'un demi-service en CPGE")], default='0207', max_length=4, verbose_name='code indemnité'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='professeur',
            name='code_indemnite',
            field=models.CharField(choices=[('0207', 'professeur en CPGE'), ('2249', "moins d'un demi-service en CPGE")], default='2249', max_length=4, verbose_name='code indemnité'),
        ),
    ]
