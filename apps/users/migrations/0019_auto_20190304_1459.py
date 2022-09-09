# Generated by Django 2.1.7 on 2019-03-04 06:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_auto_20190107_1912'),
    ]

    database_operations = [
        migrations.AlterModelTable(name='accesskey', table='authentication_accesskey'),
        migrations.AlterModelTable(name='privatetoken', table='authentication_privatetoken'),
        migrations.AlterModelTable(name='loginlog', table='audits_userloginlog'),
    ]

    state_operations = [
        migrations.DeleteModel('accesskey'),
        migrations.DeleteModel('privatetoken'),
        migrations.DeleteModel('loginlog'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations)
    ]
