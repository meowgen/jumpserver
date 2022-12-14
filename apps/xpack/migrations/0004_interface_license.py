# Generated by Django 2.1.7 on 2019-02-20 11:32

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('xpack', '0003_auto_20190121_1232'),
    ]

    operations = [
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('login_title', models.CharField(blank=True, max_length=1024, null=True, verbose_name='Заголовок страницы входа')),
                ('login_image', models.ImageField(blank=True, max_length=128, null=True, upload_to='xpack/logo/', verbose_name='Изображение страницы входа')),
                ('favicon', models.ImageField(blank=True, max_length=128, null=True, upload_to='xpack/logo/', verbose_name='Иконка')),
                ('logo_index', models.ImageField(blank=True, max_length=128, null=True, upload_to='xpack/logo/', verbose_name='Логотип главной страницы')),
                ('logo_logout', models.ImageField(blank=True, max_length=128, null=True, upload_to='xpack/logo/', verbose_name='Логотип страницы выхода')),
            ],
        ),
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('content', models.TextField(verbose_name='Содержимое')),
            ],
        ),
    ]
