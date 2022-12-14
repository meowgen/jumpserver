# Generated by Django 3.1.13 on 2021-12-30 15:04

import common.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('xpack', '0038_auto_20211207_1648'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changeauthplan',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, max_length=4096, null=True, verbose_name='SSH private key'),
        ),
        migrations.AlterField(
            model_name='changeauthplanexecution',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, max_length=4096, null=True, verbose_name='SSH private key'),
        ),
        migrations.AlterField(
            model_name='changeauthplantask',
            name='private_key',
            field=common.db.fields.EncryptTextField(blank=True, max_length=4096, null=True, verbose_name='SSH private key'),
        ),
    ]
