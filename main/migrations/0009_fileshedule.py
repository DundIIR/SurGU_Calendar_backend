# Generated by Django 4.2.13 on 2025-01-22 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_remove_customuser_is_staff_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Название файла')),
                ('file_url', models.URLField(blank=True, null=True, verbose_name='Ссылка на файл')),
            ],
            options={
                'verbose_name': 'Файл',
                'verbose_name_plural': 'Файлы',
                'ordering': ['id'],
            },
        ),
    ]
