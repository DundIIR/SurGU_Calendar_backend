from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


# Group1
# Процесс регистрации пользователя и супер-пользователя
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        role = extra_fields.get('role')
        if not role:
            role, created = Role.objects.get_or_create(name='Студент')
        extra_fields.setdefault('role', role)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault('is_superuser', True)
        admin_role, created = Role.objects.get_or_create(name='Администратор')
        extra_fields.setdefault('role', admin_role)
        return self.create_user(email, password, **extra_fields)


# Group2
#  Пользователь
class CustomUser(AbstractUser):
    username = None
    first_name = None
    last_name = None
    email = models.EmailField(unique=True, verbose_name='Email')
    password = models.CharField(max_length=128, verbose_name='Пароль')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    last_login = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name='Дата последнего входа')
    is_superuser = models.BooleanField(default=False, verbose_name='Суперпользователь')
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    is_staff = models.BooleanField(default=True, verbose_name='Стафф')

    professor = models.ForeignKey('Professor', on_delete=models.SET_NULL, blank=True, null=True,
                                  verbose_name='Преподаватель')

    student = models.ForeignKey('Student', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Студент')
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, verbose_name='Роль', related_name='users')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = '\"Пользователь\"'
        verbose_name_plural = '\"Пользователь\"'
        ordering = ['date_joined', 'last_login']


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

# Студент
class Student(models.Model):
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    course = models.CharField(max_length=100, verbose_name='Курс')
    subgroup = models.ManyToManyField('Subgroup', verbose_name='Группа/Подгруппа')

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"

    class Meta:
        verbose_name = '\"Студент\"'
        verbose_name_plural = '\"Студент\"'
        ordering = ['last_name', 'first_name', 'patronymic']


# Преподаватель
class Professor(models.Model):
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    post = models.CharField(max_length=100, verbose_name='Должность')
    department = models.ForeignKey('Department', on_delete=models.SET_DEFAULT, default=1, verbose_name='Кафедра')
    file = models.ForeignKey('FileSchedule', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Файл расписания')

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"

    class Meta:
        verbose_name = '\"Преподаватель\"'
        verbose_name_plural = '\"Преподаватель\"'
        ordering = ['last_name', 'first_name', 'patronymic']


# Group3
# Группа
class Group(models.Model):
    number_group = models.CharField(max_length=100, unique=True, verbose_name='Номер')
    speciality = models.ForeignKey('Speciality', on_delete=models.CASCADE, verbose_name='Специальность')

    def __str__(self):
        return self.number_group

    class Meta:
        verbose_name = '\"Учебная группа\"'
        verbose_name_plural = '\"Учебная группа\"'
        ordering = ['speciality', 'number_group']


# Подгруппа(группа-подгруппа)
class Subgroup(models.Model):
    group = models.ForeignKey('Group', on_delete=models.CASCADE, verbose_name='Группа')
    name_subgroup = models.CharField(max_length=100, null=True, blank=True, verbose_name='Буква')
    relations = models.ForeignKey('DivisionRelations', on_delete=models.CASCADE, verbose_name='Отношение с отделом')

    def __str__(self):
        return f"{self.group} {self.name_subgroup}"

    class Meta:
        verbose_name = '\"Учебная подгруппа\"'
        verbose_name_plural = '\"Учебная подгруппа\"'
        ordering = ['group', 'name_subgroup']


# Расписание
class Schedule(models.Model):
    start_schedule = models.DateField(verbose_name='Дата начала')
    end_schedule = models.DateField(verbose_name='Дата конца')
    subgroup = models.ForeignKey('Subgroup', on_delete=models.CASCADE, verbose_name='Группа/Подгруппа')
    file = models.ForeignKey('FileSchedule', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Файл')

    def __str__(self):
        return f"{self.subgroup}"

    class Meta:
        verbose_name = '\"Расписание\"'
        verbose_name_plural = '\"Расписание\"'
        ordering = ['start_schedule', 'subgroup']


# Занятие
class Lesson(models.Model):
    day = models.ForeignKey('Week', on_delete=models.CASCADE, verbose_name='День недели')
    time = models.ForeignKey('Time', on_delete=models.CASCADE, verbose_name='Время')
    campus = models.ForeignKey('Campus', on_delete=models.CASCADE, verbose_name='Корпус')
    audience = models.ForeignKey('Audience', on_delete=models.CASCADE, null=True, verbose_name='Аудитория')
    discipline = models.ForeignKey('Discipline', on_delete=models.CASCADE, verbose_name='Дисциплина')
    type = models.ForeignKey('Type', on_delete=models.CASCADE, null=True, verbose_name='Тип')
    repetition = models.ForeignKey('Repetition', on_delete=models.CASCADE, verbose_name='Регулярность')
    professor = models.ForeignKey('Professor', on_delete=models.SET_NULL, null=True, verbose_name='Преподаватель')
    schedule = models.ManyToManyField('Schedule', verbose_name='Номер расписания')

    def __str__(self):
        return f"{self.discipline}"

    class Meta:
        verbose_name = '\"Занятие\"'
        verbose_name_plural = '\"Занятие\"'
        ordering = ['discipline', 'day', 'time']


# Group4
#  Файл
class File(models.Model):
    file_path = models.FileField(upload_to='file/schedule/', verbose_name='Файл')

    def __str__(self):
        return f"{self.file_path.url}"

    class Meta:
        verbose_name = '\"Файл\"'
        verbose_name_plural = '\"Файл\"'
        ordering = ['id']


class FileSchedule(models.Model):
    file_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название файла")
    file_url = models.URLField(null=True, verbose_name="Ссылка на файл")



    def __str__(self):
        return f"{self.file_url}"

    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        ordering = ['id']



# Отношение с отделом
class DivisionRelations(models.Model):
    name_relations = models.CharField(max_length=100, unique=True, verbose_name='Название')

    def __str__(self):
        return self.name_relations

    class Meta:
        verbose_name = '\"Отношение с отделом\"'
        verbose_name_plural = '\"Отношение с отделом\"'


# Специальность
class Speciality(models.Model):
    cod_speciality = models.CharField(max_length=100, verbose_name='Код')
    name_speciality = models.CharField(max_length=100, verbose_name='Название')

    def __str__(self):
        return self.name_speciality

    class Meta:
        verbose_name = '\"Специальность\"'
        verbose_name_plural = '\"Специальность\"'
        ordering = ['cod_speciality', 'name_speciality']


# Кафедра
class Department(models.Model):
    number_department = models.CharField(max_length=100, unique=True, verbose_name='Номер')
    name_department = models.CharField(max_length=100, unique=True, verbose_name='Название')
    phone_department = models.CharField(max_length=100, unique=True, verbose_name='Телефон')
    email_department = models.EmailField(unique=True, verbose_name='Email')
    head_department = models.CharField(max_length=100, unique=True, verbose_name='Заведующий')

    def __str__(self):
        return self.name_department

    class Meta:
        verbose_name = '\"Кафедра\"'
        verbose_name_plural = '\"Кафедра\"'
        ordering = ['name_department']


# Дисциплина
class Discipline(models.Model):
    name_discipline = models.CharField(max_length=100, verbose_name='Название')

    def __str__(self):
        return self.name_discipline

    class Meta:
        verbose_name = '\"Дисциплина\"'
        verbose_name_plural = '\"Дисциплина\"'
        ordering = ['name_discipline']


# Тип
class Type(models.Model):
    name_type = models.CharField(max_length=100, unique=True, verbose_name='Тип')

    def __str__(self):
        return self.name_type

    class Meta:
        verbose_name = '\"Тип пары\"'
        verbose_name_plural = '\"Тип пары\"'
        ordering = ['name_type']


# Регулярность
class Repetition(models.Model):
    name_repetition = models.CharField(max_length=100, verbose_name='Регулярность')
    repetition_reduction = models.CharField(max_length=100, verbose_name='Сокращение')

    def __str__(self):
        return self.name_repetition

    class Meta:
        verbose_name = '\"Регулярность повторения занятия\"'
        verbose_name_plural = '\"Регулярность повторения занятия\"'
        ordering = ['name_repetition']


# Аудитория
class Audience(models.Model):
    number_audience = models.CharField(max_length=100, unique=True, verbose_name='Номер')

    def __str__(self):
        return self.number_audience

    class Meta:
        verbose_name = '\"Аудитория\"'
        verbose_name_plural = '\"Аудитория\"'
        ordering = ['number_audience']


# День недели
class Week(models.Model):
    day_of_week = models.CharField(max_length=100, verbose_name='Название')
    day_reduction = models.CharField(max_length=100, verbose_name='Сокращение')

    def __str__(self):
        return self.day_reduction

    class Meta:
        verbose_name = '\"Дни недели\"'
        verbose_name_plural = '\"Дни недели\"'
        ordering = ['id']


# Корпус
class Campus(models.Model):
    name_campus = models.CharField(max_length=100, verbose_name='Название')
    reduction = models.CharField(max_length=100, verbose_name='Сокращение')
    time_group = models.ForeignKey('TimeGroup', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='Номер группы расписания звонков')

    def __str__(self):
        return self.reduction

    class Meta:
        verbose_name = '\"Корпус\"'
        verbose_name_plural = '\"Корпус\"'
        ordering = ['name_campus']


# Номер группы расписания звонков
class TimeGroup(models.Model):
    number_time_group = models.IntegerField(unique=True, verbose_name='Номер')

    def __str__(self):
        return f"{self.number_time_group}"

    class Meta:
        verbose_name = '\"Группа расписания звонков\"'
        verbose_name_plural = '\"Группа расписания звонков\"'
        ordering = ['number_time_group']


# Время занятия
class Time(models.Model):
    time_start = models.TimeField(verbose_name='Время начала пары')
    time_end = models.TimeField(verbose_name='Время конца пары')
    time_out = models.TimeField(verbose_name='Время перерыва')
    number_lesson = models.IntegerField(verbose_name='Номер пары')
    time_group = models.ForeignKey('TimeGroup', on_delete=models.CASCADE,
                                   verbose_name='Номер группы расписания звонков')

    def __str__(self):
        return f"{self.number_lesson}"

    class Meta:
        verbose_name = '\"Расписание звонков\"'
        verbose_name_plural = '\"Расписание звонков\"'
        ordering = ['time_group', 'number_lesson']