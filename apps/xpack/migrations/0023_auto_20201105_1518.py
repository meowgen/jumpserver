# Generated by Django 2.2.13 on 2020-11-05 07:18

from django.db import migrations, models
import common.db.fields
import django_mysql.models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('xpack', '0022_auto_20200921_1101'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='attrs',
            field=django_mysql.models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='account',
            name='provider',
            field=models.CharField(choices=[('aliyun', 'Alibaba Cloud'), ('qcloud', 'Tencent Cloud'), ('aws_china', 'AWS (China)'), ('aws_international', 'AWS (International)'), ('huaweicloud', 'Huawei Cloud'), ('azure', 'Azure (China)')], default='aliyun', max_length=128, verbose_name='Provider'),
        ),
        migrations.AlterField(
            model_name='changeauthplan',
            name='password_rules',
            field=common.db.fields.JsonDictCharField(default={'length': 30}, max_length=2048, verbose_name='Password rules'),
        ),
        migrations.AlterField(
            model_name='syncinstancedetail',
            name='asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.Asset', verbose_name='Asset'),
        )
    ]
