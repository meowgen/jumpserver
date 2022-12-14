# Generated by Django 2.1.7 on 2019-07-11 12:18

import common.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0034_auto_20190705_1348'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminuser',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, null=True, verbose_name='SSH private key'),
        ),
        migrations.AlterField(
            model_name='authbook',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, null=True, verbose_name='SSH private key'),
        ),
        migrations.AlterField(
            model_name='gateway',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, null=True, verbose_name='SSH private key'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, null=True, verbose_name='SSH private key'),
        ),
    ]
