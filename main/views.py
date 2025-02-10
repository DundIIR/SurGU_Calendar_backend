import os

import boto3
from django.db.models import Q
from django.shortcuts import render
from rest_framework import generics
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from urllib.parse import unquote

from .authentication import IsAdminUserRole
from .models import *
from .serializers import LessonSerializer, SubgroupSerializer, ProfessorSerializer, CustomUserSerializer, \
    UserListSerializer, FileSerializer

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound
from rest_framework.authentication import BaseAuthentication

from django.conf import settings

import uuid
from datetime import datetime

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'path.to.BearerAuthentication',
    ],
}


def index(request):
    return render(request, 'index.html')

import re
def split_by_letter(input_string):
    pattern = r"^\d{3}-\d{2}[а-яА-Я]$"

    # ФИО, разделенное по пробелам: Кузин Дмитрий Александрович
    if ' ' in input_string:
        return input_string.split(' ')
    # Группа с подгруппой из одной буквы: 609-11а
    elif re.search(pattern, input_string):
        return [input_string[:-1], input_string[-1]]
    # Группа без подгруппы: 609-11
    return [input_string]

# Контроллер для получения расписания с фильтрацией
class LessonAPIList(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LessonSerializer

    def get_queryset(self):
        print('Начинаем поиск расписания')
        search_query = self.request.GET.get('search', '')
        print(search_query)
        if search_query:
            request_list = split_by_letter(search_query)
            if len(request_list) <= 3:
                return search_lessons(self, *request_list)
        return None


# Контроллер для получения списка групп с фильтрацией
class SubgroupListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = SubgroupSerializer  # Сериализатор для подгрупп

    def get_queryset(self):
        search_query = self.request.GET.get('search', '')
        if search_query:
            groups = Group.objects.filter(number_group__startswith=search_query)
            return Subgroup.objects.filter(group__in=groups)
        return Subgroup.objects.all()


# Контроллер для получения списка преподавателей с фильтрацией
class ProfessorListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ProfessorSerializer

    def get_queryset(self):
        search_query = self.request.GET.get('search', '')  # Получаем параметр search
        if search_query:
            return Professor.objects.filter(
                Q(last_name__startswith=search_query) |
                Q(first_name__startswith=search_query) |
                Q(patronymic__startswith=search_query)
            )
        return Professor.objects.all()


def search_lessons(self, attr1, attr2=None, attr3=None):
    print('Составляем расписание')
    if attr3:
        search_results = Professor.objects.get(last_name=attr1, first_name=attr2, patronymic=attr3)
        lessons = Lesson.objects.filter(professor=search_results)
    elif attr2:
        lessons1 = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1,
                                         schedule__subgroup__name_subgroup=attr2)
        lessons2 = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1,
                                         schedule__subgroup__name_subgroup='0')
        lessons = lessons1.union(lessons2)
    else:
        lessons = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1)
        print(lessons, attr1)
    return lessons


# Проверка авторизации пользователя
class ProtectedDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response({
            'user': serializer.data
        })


class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsAdminUserRole]


class UpdateUserRoleAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def post(self, request):
        email = request.data.get('email')
        role_name = request.data.get('role')

        if not email or not role_name:
            raise ValidationError({'error': 'Поля email и role обязательны.'})

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise NotFound({'error': f'Пользователь с email {email} не найден.'})

        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            raise NotFound({'error': f'Роль с именем {role_name} не найдена.'})

        user.role = role
        user.save()

        return Response({'message': f'Роль пользователя {email} успешно обновлена на {role_name}.'})


# class FileUploadAPIView(APIView):
#     authentication_classes = []
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser]
#     def post(self, request):
#         files = request.FILES.getlist('files')
#
#         s3_client = boto3.client(
#             's3',
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             endpoint_url=settings.AWS_END_POINT,
#             region_name=settings.AWS_REGION,
#
#         )
#
#         uploaded_files = []
#
#         for file in files:
#             print(file)
#             try:
#                 s3_client.upload_fileobj(
#                     Fileobj=file,
#                     Bucket=settings.AWS_BUCKET,
#                     Key=file.name,
#                     ExtraArgs={'ContentType': file.content_type}
#                 )
#                 uploaded_files.append(file.name)
#             except Exception as e:
#                 return Response({'error': f'Ошибка загрузки файла {file.name}: {str(e)}'}, status=500)
#
#         return Response({
#             'message': 'Файлы успешно загружены в Yandex Object Storage.',
#             'uploaded_files': uploaded_files
#         })


# class FileUploadAPIView(APIView):
#     authentication_classes = []
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser]
#
#     def post(self, request):
#         # Проверка наличия файлов в запросе
#         files = request.FILES.getlist('files')
#         if not files:
#             return Response({'error': 'Файлы не были загружены.'}, status=400)
#
#         s3_client = boto3.client(
#             's3',
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             endpoint_url=settings.AWS_END_POINT,
#             region_name=settings.AWS_REGION,
#         )
#
#         uploaded_files = []
#
#         for file in files:
#             # Валидация: Проверка типа файла
#             if not file.name.endswith('.pdf'):  # пример для PDF файлов
#                 return Response({'error': f'Неверный тип файла: {file.name}. Требуется PDF.'}, status=400)
#
#             # Валидация: Проверка длина названия
#             if len(file.name) > 250:
#                 return Response(
#                     {
#                         'error': f'Название файла слишком длинное, {len(file.name)} символов. Максимум 250 символов.'},
#                     status=400
#                 )
#
#             # Валидация: Проверка размера файла (например, 5MB)
#             if file.size > 5 * 1024 * 1024:  # 5MB
#                 return Response({'error': f'Файл {file.name} слишком большой. Максимальный размер: 5MB.'}, status=400)
#
#             # Генерация уникального имени файла
#             unique_name = str(uuid.uuid4()) + '.pdf'
#
#             try:
#                 # Загрузка файла в S3
#                 s3_client.upload_fileobj(
#                     Fileobj=file,
#                     Bucket=settings.AWS_BUCKET,
#                     Key=unique_name,
#                     ExtraArgs={'ContentType': file.content_type}
#                 )
#
#                 # Формирование URL для загруженного файла
#                 file_url = f"{settings.AWS_END_POINT}/{settings.AWS_BUCKET}/{unique_name}"
#
#                 # Добавление записи в БД
#                 file_record = FileSchedule(file_name=file.name, file_url=file_url)
#                 file_record.save()
#
#                 # Добавление в список успешных файлов
#                 uploaded_files.append(file.name)
#             except Exception as e:
#                 return Response({'error': f'Файл {file.name} не загрузился: {str(e)}'}, status=500)
#
#         # Возвращаем успешный ответ
#         return Response({
#             'message': 'Файлы успешно загружены в Yandex Object Storage.',
#             'uploaded_files': uploaded_files
#         })

from io import BytesIO
from .parser.parse_schedule import process_schedule

class UploadAndProcessScheduleAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # Проверка наличия файлов
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'Файлы не были загружены.'}, status=400)

        # Получаем параметр "страниц" из запроса
        pages_param = request.data.get('pages', '').strip()
        specific_page = None
        page_range = None

        # Парсинг параметра "страниц"
        if '-' in pages_param:
            # Если указан диапазон "4-7"
            try:
                start, end = map(int, pages_param.split('-'))
                if start > end:
                    start, end = end, start  # Если первая цифра больше второй
                page_range = (start, end)
            except ValueError:
                return Response({'error': 'Неверный формат выбора страниц.'}, status=400)
        elif pages_param:
            # Если указана одна страница
            try:
                specific_page = int(pages_param)
            except ValueError:
                return Response({'error': 'Неверный формат выбора страниц.'}, status=400)

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_END_POINT,
            region_name=settings.AWS_REGION,
        )

        uploaded_files = []

        for file in files:
            # Проверка типа файла
            if not file.name.endswith('.pdf'):
                return Response({'error': f'Неверный тип файла: {file.name}. Требуется PDF.'}, status=400)

            # Проверка длины названия
            if len(file.name) > 250:
                return Response({'error': f'Название файла слишком длинное ({len(file.name)} символов). Максимум 250 символов.'}, status=400)

            # Проверка размера файла
            if file.size > 10 * 1024 * 1024:  # 10MB
                return Response({'error': f'Файл {file.name} слишком большой. Максимальный размер: 10MB.'}, status=400)

            # Генерация уникального имени файла
            unique_name = str(uuid.uuid4()) + '.pdf'

            try:
                # # Загрузка файла в S3
                # s3_client.upload_fileobj(
                #     Fileobj=file,
                #     Bucket=settings.AWS_BUCKET,
                #     Key=unique_name,
                #     ExtraArgs={'ContentType': file.content_type}
                # )

                file_content = BytesIO(file.read())

                # Обработка файла из памяти
                try:
                    # Параметры для process_schedule (замените на ваши данные)
                    type_campus = ['ЭОиДОТ', 'С']
                    type_subgroup = ['0', 'а', 'б', 'в', 'г']
                    type_abbreviations = {
                        'пр': 'практика',
                        'лек': 'лекция',
                        'лаб': 'лаба',
                        'CDIO': 'CDIO'
                    }

                    json_path = '../other_files/professor_availability.json'

                    schedule_data = process_schedule(
                        path_pdf=file_content,
                        type_campus=type_campus,
                        type_subgroup=type_subgroup,
                        type_abbreviations=type_abbreviations,
                        specific_page=specific_page,
                        page_range=page_range
                    )

                    # Добавление данных в БД
                    if schedule_data:
                        result = schedule_data

                except Exception as e:
                    return Response({'error': f'Ошибка обработки файла {file.name}: {str(e)}'}, status=500)

                # Формирование URL для загруженного файла
                file_url = f"{settings.AWS_END_POINT}/{settings.AWS_BUCKET}/{unique_name}"

                # # Добавление записи о файле в БД (если нужно)
                # FileSchedule.objects.create(file_name=file.name, file_url=file_url)

                uploaded_files.append({'file_name': file.name, 'file_url': file_url, 'db_status': result})

            except Exception as e:
                return Response({'error': f'Ошибка загрузки файла {file.name}: {str(e)}'}, status=500)

        return Response({
            'message': 'Файлы успешно обработаны и загружены.',
            'details': uploaded_files
        })


class FileListAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        files = FileSchedule.objects.all()
        serializer = FileSerializer(files, many=True)
        return Response(serializer.data)


from datetime import datetime
from django.db import IntegrityError
def add_schedule_data(data):
    print('Данные получены')
    try:
        for speciality_code, speciality_data in data.items():
            # 1. Получаем или создаем специальность
            speciality, created = Speciality.objects.get_or_create(
                cod_speciality=speciality_code,
                name_speciality=speciality_data['name_speciality']
            )

            for group_code, group_data in speciality_data['groups'].items():
                # 2. Получаем или создаем группу
                group, created = Group.objects.get_or_create(
                    number_group=group_code,
                    speciality=speciality
                )

                for subgroup_code, subgroup_data in group_data['subgroup'].items():
                    # 3. Получаем или создаем подгруппу
                    relations, created_relation = DivisionRelations.objects.get_or_create(
                        name_relations="По количеству людей"
                    )

                    subgroup, created = Subgroup.objects.get_or_create(
                        group=group,
                        name_subgroup=subgroup_code, # Добавить проверку, если код ноль, то присвоить NULL
                        defaults={'relations': relations}
                    )

                    # 4. Создаем расписание
                    schedule, created = Schedule.objects.get_or_create(
                        start_schedule=datetime.strptime(group_data['schedule']['start_schedule'], '%d.%m.%Y'),
                        end_schedule=datetime.strptime(group_data['schedule']['end_schedule'], '%d.%m.%Y'),
                        subgroup=subgroup
                    )

                    # Проходим по каждому дню недели
                    for weekday, lessons in subgroup_data.items():
                        # Проходим по каждому номеру пары
                        for lesson_time, lesson_data in lessons.items():
                            # 5. Проходим по каждому занятию
                            for lesson_repetition, lesson_info in lesson_data.items():

                                # 5.1 Получаем или создаем преподавателя
                                last_name, first_name_and_patronymic = lesson_info['professor_id'].split()
                                first_name, patronymic = first_name_and_patronymic.split('.')[:2]

                                professor = Professor.objects.filter(
                                    last_name=last_name,
                                    first_name__startswith=first_name,
                                    patronymic__startswith=patronymic
                                ).first()

                                if not professor:
                                    professor = Professor.objects.create(
                                        last_name=last_name,
                                        first_name=first_name,
                                        patronymic=patronymic,
                                        post="Неизвестно",  # Должность неизвестна
                                        department_id=1  # департамент 1
                                    )

                                # 5.2 Получаем или создаем аудиторию
                                if lesson_info['audience_id']:
                                    audience, created = Audience.objects.get_or_create(
                                        number_audience=lesson_info['audience_id']
                                    )
                                else:
                                    audience = None

                                # 5.3 Получаем или создаем дисциплину
                                discipline, created = Discipline.objects.get_or_create(
                                    name_discipline=lesson_info['discipline_id']
                                )

                                # 5.4 Получаем или создаем тип занятия
                                type, created = Type.objects.get_or_create(
                                    name_type=lesson_info['type_id']
                                )

                                # 5.5 Получаем день недели
                                day_of_week = Week.objects.get(day_reduction=weekday)
                                print(day_of_week)


                                # 5.6 Получаем повторяемость
                                # repetition = Repetition.objects.filter(
                                #     repetition_reduction=lesson_repetition).first()
                                # if not repetition:
                                #     repetition = Repetition.objects.create(
                                #         repetition_reduction=lesson_repetition,
                                #         name_repetition='Неизвестная регулярность'
                                #     )

                                repetition, created = Repetition.objects.get_or_create(
                                    repetition_reduction=lesson_repetition,
                                    defaults={
                                        'name_repetition': 'Неизвестная регулярность'
                                    }
                                )

                                # 5.7 Получаем корпус
                                campus, created = Campus.objects.get_or_create(
                                    reduction=lesson_info['campus_id'],
                                    defaults={
                                        'name_campus': lesson_info['campus_id'],
                                        'time_group_id': 1
                                    }
                                )

                                # 5.7 Получаем время пары
                                time_group = campus.time_group

                                number_lesson = Time.objects.get(
                                    time_group=time_group,
                                    number_lesson=lesson_time
                                )

                                print(number_lesson, day_of_week, campus, audience, discipline, type, repetition, professor)

                                # 6. Создаем запись о занятии
                                lesson, created = Lesson.objects.get_or_create(
                                    time=number_lesson,
                                    day=day_of_week,
                                    campus=campus,
                                    audience=audience,
                                    discipline=discipline,
                                    type=type,
                                    repetition=repetition,
                                    professor=professor
                                )

                                # 7. Связываем расписание с занятием
                                lesson.schedule.add(schedule)

        return "Данные успешно добавлены в БД"

    except IntegrityError as e:
        print('Ошибка', e)
        return f"Integrity Error: {e}"
    except Exception as e:
        print('Ошибка 2', e)
        return f"Error: {e}"


