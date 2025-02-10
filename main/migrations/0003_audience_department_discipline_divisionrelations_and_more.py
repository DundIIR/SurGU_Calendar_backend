# Generated by Django 4.2.13 on 2024-05-19 05:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_professor_student_customuser_professor_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Audience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_audience', models.CharField(max_length=100, unique=True, verbose_name='Номер')),
            ],
            options={
                'verbose_name': '"Аудитория"',
                'verbose_name_plural': '"Аудитория"',
                'ordering': ['number_audience'],
            },
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_department', models.CharField(max_length=100, unique=True, verbose_name='Номер')),
                ('name_department', models.CharField(max_length=100, unique=True, verbose_name='Название')),
                ('phone_department', models.CharField(max_length=100, unique=True, verbose_name='Телефон')),
                ('email_department', models.EmailField(max_length=254, unique=True, verbose_name='Email')),
                ('head_department', models.CharField(max_length=100, unique=True, verbose_name='Заведующий')),
            ],
            options={
                'verbose_name': '"Кафедра"',
                'verbose_name_plural': '"Кафедра"',
                'ordering': ['name_department'],
            },
        ),
        migrations.CreateModel(
            name='Discipline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_discipline', models.CharField(max_length=100, verbose_name='Название')),
            ],
            options={
                'verbose_name': '"Дисциплина"',
                'verbose_name_plural': '"Дисциплина"',
                'ordering': ['name_discipline'],
            },
        ),
        migrations.CreateModel(
            name='DivisionRelations',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_relations', models.CharField(max_length=100, unique=True, verbose_name='Название')),
            ],
            options={
                'verbose_name': '"Отношение с отделом"',
                'verbose_name_plural': '"Отношение с отделом"',
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_path', models.FileField(upload_to='file/schedule/', verbose_name='Файл')),
            ],
            options={
                'verbose_name': '"Файл"',
                'verbose_name_plural': '"Файл"',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Repetition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_repetition', models.CharField(max_length=100, unique=True, verbose_name='Регулярность')),
            ],
            options={
                'verbose_name': '"Регулярность повторения занятия"',
                'verbose_name_plural': '"Регулярность повторения занятия"',
                'ordering': ['name_repetition'],
            },
        ),
        migrations.CreateModel(
            name='Speciality',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cod_speciality', models.CharField(max_length=100, verbose_name='Код')),
                ('name_speciality', models.CharField(max_length=100, verbose_name='Название')),
            ],
            options={
                'verbose_name': '"Специальность"',
                'verbose_name_plural': '"Специальность"',
                'ordering': ['cod_speciality', 'name_speciality'],
            },
        ),
        migrations.CreateModel(
            name='TimeGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_time_group', models.IntegerField(unique=True, verbose_name='Номер')),
            ],
            options={
                'verbose_name': '"Группа расписания звонков"',
                'verbose_name_plural': '"Группа расписания звонков"',
                'ordering': ['number_time_group'],
            },
        ),
        migrations.CreateModel(
            name='Type',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_type', models.CharField(max_length=100, unique=True, verbose_name='Тип')),
            ],
            options={
                'verbose_name': '"Тип пары"',
                'verbose_name_plural': '"Тип пары"',
                'ordering': ['name_type'],
            },
        ),
        migrations.CreateModel(
            name='Week',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.CharField(max_length=100, verbose_name='Название')),
                ('day_reduction', models.CharField(max_length=100, verbose_name='Сокращение')),
            ],
            options={
                'verbose_name': '"Дни недели"',
                'verbose_name_plural': '"Дни недели"',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Time',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_start', models.TimeField(verbose_name='Время начала пары')),
                ('time_end', models.TimeField(verbose_name='Время конца пары')),
                ('time_out', models.TimeField(verbose_name='Время перерыва')),
                ('number_lesson', models.IntegerField(verbose_name='Номер пары')),
                ('time_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.timegroup', verbose_name='Номер группы расписания звонков')),
            ],
            options={
                'verbose_name': '"Расписание звонков"',
                'verbose_name_plural': '"Расписание звонков"',
                'ordering': ['time_group', 'number_lesson'],
            },
        ),
        migrations.CreateModel(
            name='Campus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_campus', models.CharField(max_length=100, verbose_name='Название')),
                ('reduction', models.CharField(max_length=100, verbose_name='Сокращение')),
                ('time_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.timegroup', verbose_name='Номер группы расписания звонков')),
            ],
            options={
                'verbose_name': '"Корпус"',
                'verbose_name_plural': '"Корпус"',
                'ordering': ['name_campus'],
            },
        ),
        migrations.AddField(
            model_name='professor',
            name='department',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.SET_DEFAULT, to='main.department', verbose_name='Кафедра'),
        ),
        migrations.AddField(
            model_name='professor',
            name='file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.file', verbose_name='Файл расписания'),
        ),
    ]
