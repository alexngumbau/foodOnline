# Generated by Django 5.0.6 on 2024-06-03 20:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_userprofile_cover_photo'),
        ('vendor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='userProfile',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='userprofile', to='accounts.userprofile'),
        ),
    ]
