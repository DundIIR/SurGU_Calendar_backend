# Generated by Django 4.2.13 on 2024-05-19 05:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Professor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_name', models.CharField(max_length=100, verbose_name='Фамилия')),
                ('first_name', models.CharField(max_length=100, verbose_name='Имя')),
                ('patronymic', models.CharField(max_length=100, verbose_name='Отчество')),
                ('post', models.CharField(max_length=100, verbose_name='Должность')),
            ],
            options={
                'verbose_name': '"Преподаватель"',
                'verbose_name_plural': '"Преподаватель"',
                'ordering': ['last_name', 'first_name', 'patronymic'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_name', models.CharField(max_length=100, verbose_name='Фамилия')),
                ('first_name', models.CharField(max_length=100, verbose_name='Имя')),
                ('patronymic', models.CharField(max_length=100, verbose_name='Отчество')),
                ('course', models.CharField(max_length=100, verbose_name='Курс')),
            ],
            options={
                'verbose_name': '"Студент"',
                'verbose_name_plural': '"Студент"',
                'ordering': ['last_name', 'first_name', 'patronymic'],
            },
        ),
        migrations.AddField(
            model_name='customuser',
            name='professor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.professor', verbose_name='Преподаватель'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.student', verbose_name='Студент'),
        ),
    ]
