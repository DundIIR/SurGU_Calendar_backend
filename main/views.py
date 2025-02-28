import os
import boto3
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from urllib.parse import unquote
from .authentication import IsAdminUserRole
from .models import *
from .serializers import LessonSerializer, SubgroupSerializer, ProfessorSerializer, CustomUserSerializer, \
    UserListSerializer, FileSerializer, GroupSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import AuthenticationFailed, ValidationError, NotFound
from rest_framework.authentication import BaseAuthentication
from django.conf import settings
import uuid
from datetime import datetime, timedelta
from datetime import datetime
import re

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'path.to.BearerAuthentication',
    ],
}


def index(request):
    return render(request, 'index.html')


## БЕЗ РЕГИСТРАЦИИ


# Контроллер для получения списка всех групп
class GroupList(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        groups = Group.objects.values_list('number_group', flat=True)
        return Response(list(groups))


# Контроллер для получения списка всех преподавателей
class ProfessorsList(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        professors = Professor.objects.all()
        full_names = [f"{prof.last_name} {prof.first_name} {prof.patronymic}" for prof in professors]
        return Response(full_names)


# Контроллер для проверки запроса
class SearchCheck(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('search', '')

        if query:
            first_char = query[0]

            # Если первая цифра
            if first_char.isdigit():
                group = get_object_or_404(Group, number_group=query)
                subgroups = Subgroup.objects.filter(group=group)
                subgroup_numbers = [subgroup.name_subgroup for subgroup in subgroups]
                if subgroup_numbers:
                    return Response(subgroup_numbers)
                else:
                    return Response({"message": "Нет подгрупп"}, status=404)

            # Если первая буква
            elif first_char.isalpha():

                name_parts = query.split()

                # Примерные формы ввода:
                # "Емельянов С Н", "Емельянов Сергей Николаевич", "Емельянов", "Емельянов Сергей"
                if len(name_parts) == 1:
                    # Только фамилия
                    professors = Professor.objects.filter(last_name__icontains=name_parts[0])
                elif len(name_parts) == 2:
                    # Фамилия + инициалы/имя
                    professors = Professor.objects.filter(
                        Q(last_name__icontains=name_parts[0]) &
                        (Q(first_name__icontains=name_parts[1]) | Q(patronymic__icontains=name_parts[1]))
                    )
                elif len(name_parts) == 3:
                    # Фамилия + имя + отчество
                    professors = Professor.objects.filter(
                        Q(last_name__icontains=name_parts[0]) &
                        Q(first_name__icontains=name_parts[1]) &
                        Q(patronymic__icontains=name_parts[2])
                    )
                else:
                    return Response({"message": "Неверный формат запроса"}, status=400)

                professor_names = [f"{prof.last_name} {prof.first_name} {prof.patronymic}" for prof in professors]
                if professor_names:
                    return Response(professor_names)
                else:
                    return Response({"message": "Преподаватель не найден"}, status=404)

        return Response({"message": "Неверный запрос"}, status=400)


class ScheduleFileView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        search = request.query_params.get('search', '')
        subgroup = request.query_params.get('subgroup', None)
        professors = request.query_params.get('professors', 'false').lower() == 'true'

        if not search:
            return Response({"message": "Поле 'search' обязательно"}, status=400)

        print(search, subgroup, professors)

        if professors:
            professor = self.get_professor(search)
            if not professor:
                return Response({"message": "Преподаватель не найден"}, status=404)
            schedule = Lesson.objects.filter(professor=professor)
            filename = f"schedule_{professor.last_name}.ics"
            schedule_obj = Schedule.objects.filter(professor=professor).first()
        else:


            group = Group.objects.filter(number_group=search).first()
            if not group:
                return Response({"message": "Группа не найдена"}, status=404)

            # Получаем подгруппу, если указана
            if subgroup and subgroup.lower() != "none":
                subgroup = Subgroup.objects.filter(group=group, name_subgroup=subgroup).first()
                if not subgroup:
                    return Response({"message": "Подгруппа не найдена"}, status=404)
            else:
                subgroup = None

            # 2. Находим расписание для этой группы и подгруппы
            schedule = Schedule.objects.filter(subgroup=subgroup).first()
            if not schedule:
                return Response({"message": "Расписание не найдено"}, status=404)

            # if schedule.file:
            #     file_path = schedule.file.file_path.path
            # else:
            if True:
                # 4. Генерируем новый файл
                file_path = self.create_ics_file(schedule)
                # Сохраняем файл в БД
                new_file = File(file_path=file_path)
                new_file.save()
                schedule.file = new_file
                schedule.save()

            # 5. Отправляем файл пользователю
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))

        # if not schedule.exists():
        #     return Response({"message": "Расписание не найдено"}, status=404)
        #
        # # Проверка наличия файла в БД
        # if schedule_obj and schedule_obj.file:
        #     file_path = schedule_obj.file.path
        # else:
        #     file_path = os.path.join(settings.MEDIA_ROOT, "schedule", filename)
        #     if not os.path.exists(file_path):
        #         self.create_ics_file(schedule, file_path)
        #
        #     # Сохранение файла в БД
        #     new_file = File()
        #     new_file.file = file_path
        #     new_file.save()
        #     if schedule_obj:
        #         schedule_obj.file = new_file
        #         schedule_obj.save()
        #
        # return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)



    def get_professor(self, search):
        parts = search.split()
        if len(parts) == 1:
            return Professor.objects.filter(last_name__icontains=parts[0]).first()
        elif len(parts) == 2:
            return Professor.objects.filter(last_name__icontains=parts[0], first_name__icontains=parts[1]).first()
        elif len(parts) == 3:
            return Professor.objects.filter(last_name=parts[0], first_name=parts[1], patronymic=parts[2]).first()
        return None

    def get_group_schedule(self, group, subgroup):
        if subgroup and subgroup.lower() != "none":
            lessons1 = Lesson.objects.filter(schedule__group_subgroup__group__group_number=group,
                                             schedule__group_subgroup__subgroup_name=subgroup)
            lessons2 = Lesson.objects.filter(schedule__group_subgroup__group__group_number=group,
                                             schedule__group_subgroup__subgroup_name=None)
            lessons = lessons1.union(lessons2)
            return lessons
        return Lesson.objects.filter(schedule__group_subgroup__group__group_number=group)

    def create_ics_file(self, schedule):
        list_days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
        time_zone = 'Asia/Yekaterinburg:'

        # Путь к base.txt
        print('Расписание нашлось', schedule)
        base_path = os.path.join(settings.STATIC_ROOT, "file", "base.txt")

        events = []

        # Берём первое расписание и определяем дату его начала
        record = schedule
        start_schedule = record.start_schedule
        id_week_of_day = start_schedule.weekday()  # День недели (0 - понедельник, 6 - воскресенье)

        for lesson in record.lesson_set.all():
            # Определяем день недели для урока
            id_week_of_day_lesson = list_days_of_week.index(str(lesson.day))

            # Рассчитываем разницу в днях
            if id_week_of_day_lesson >= id_week_of_day:
                plus_days = id_week_of_day_lesson - id_week_of_day
                flag = True
            else:
                plus_days = id_week_of_day_lesson - id_week_of_day + 7
                flag = False

            # Определяем дату первого занятия
            if lesson.repetition in ['Числитель', 'Каждую неделю'] and flag:
                date_start_lesson = start_schedule + timedelta(days=plus_days)
            elif lesson.repetition in ['Знаменатель', 'Каждую неделю'] and not flag:
                date_start_lesson = start_schedule + timedelta(days=plus_days)
            else:
                date_start_lesson = start_schedule + timedelta(days=plus_days + 7)

            # Определяем правило повторения
            repetition = "FREQ=WEEKLY"
            if lesson.repetition in ['Числитель', 'Знаменатель']:
                repetition += ";INTERVAL=2"

            # Формируем строки события
            start_time = date_start_lesson.strftime("%Y%m%dT") + lesson.time.time_start.strftime("%H%M%S")
            end_time = date_start_lesson.strftime("%Y%m%dT") + lesson.time.time_end.strftime("%H%M%S")

            event = (
                "BEGIN:VEVENT\n"
                f"DTSTART;TZID={time_zone}{start_time}\n"
                f"DTEND;TZID={time_zone}{end_time}\n"
                f"SUMMARY:{lesson.discipline}\n"
                f"DESCRIPTION:{lesson.professor}\n"
                f"LOCATION:{lesson.campus} {lesson.audience}\n"
                f"RRULE:{repetition}\n"
                "END:VEVENT"
            )
            events.append(event)
        print(events)
        # Читаем base.txt
        with open(base_path, 'r', encoding='utf-8') as file:
            base_content = file.readlines()

        # Вставляем события перед `END:VCALENDAR`
        insert_index = base_content.index("END:VCALENDAR")
        final_content = base_content[:insert_index] + events + [base_content[insert_index]]

        # Определяем путь сохранения
        file_name = f"schedule_{record.subgroup.group.number_group}.ics"
        file_path = os.path.join(settings.MEDIA_ROOT, "schedule", file_name)

        # Создаём папку, если её нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Записываем в файл
        with open(file_path, 'w', encoding='utf-8') as ics_file:
            ics_file.write("".join(final_content))

        return file_path


#
# def create_file(record, lesson):
#     id_week_of_day = record.start_schedule.weekday()
#     id_week_of_day_lesson = list_days_of_week.index(str(lesson.day))
#     if id_week_of_day_lesson >= id_week_of_day:
#         plus_days = id_week_of_day_lesson - id_week_of_day
#         flag = True
#     else:
#         plus_days = id_week_of_day_lesson - id_week_of_day + 7
#         flag = False
#
#     if str(lesson.repetition) in ['Числитель', 'Каждую неделю'] and flag:
#         date_start_lesson = record.start_schedule + timedelta(days=plus_days)
#     elif str(lesson.repetition) in ['Знаменатель', 'Каждую неделю'] and not flag:
#         date_start_lesson = record.start_schedule + timedelta(days=plus_days)
#     else:
#         date_start_lesson = record.start_schedule + timedelta(days=plus_days + 7)
#
#     repetition = ''
#     if str(lesson.repetition) in ['Числитель', 'Знаменатель']:
#         repetition = ';INTERVAL=2'
#     return file_collection(date_start_lesson, repetition, record, lesson)
#
# def file_collection(date_start_lesson, repetition, record, lesson):
#     part_base_path = os.path.join(settings.STATIC_ROOT, 'file', 'part_base.txt')
#     list_attrs = [time_zone+str(date_start_lesson.strftime('%Y%m%d'))+'T'+str(lesson.time.time_start.strftime('%H%M%S')),
#                   time_zone+str(date_start_lesson.strftime('%Y%m%d'))+'T'+str(lesson.time.time_end.strftime('%H%M%S')),
#                   str(record.end_schedule.strftime('%Y%m%d')) + 'T235959' + repetition,
#                   str(datetime.now().strftime('%Y%m%d')),
#                   '<b>' + str(lesson.professor) + '</b><br>' + replace_none(record),
#                   str(lesson.campus)+str(lesson.audience) + ' ' + str(lesson.type),
#                   str(lesson.discipline)]
#     with open(part_base_path, 'r') as file:
#         content = file.readlines()
#         for i in range(1, len(content)-5):
#             f = content[i][:-1]
#             f += str(list_attrs[i-1]) + '\n'
#             content[i] = f
#     return content
#
# def full_file(list_lessons, name):
#     name_file = 'Расписание '+name
#     base_path = os.path.join(settings.STATIC_ROOT, 'file', 'base.txt')
#
#     with open(base_path, 'r') as file:
#         full_content = file.readlines()
#         content = full_content[:-1]
#         end_content = full_content[-1]
#         content += list_lessons
#         content += end_content
#
#     content_str = ''.join(content)
#     encoded_content = content_str.encode('utf-8')
#     save_path = 'file/schedule/' + name_file + '.ics'
#     default_storage.save(save_path, ContentFile(encoded_content))
#     return save_path
#
#
#
#




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
                return Response(
                    {'error': f'Название файла слишком длинное ({len(file.name)} символов). Максимум 250 символов.'},
                    status=400)

            # Проверка размера файла
            if file.size > 10 * 1024 * 1024:  # 10MB
                return Response({'error': f'Файл {file.name} слишком большой. Максимальный размер: 10MB.'}, status=400)

            # Генерация уникального имени файла
            unique_name = str(uuid.uuid4()) + '.pdf'

            try:
                # Загрузка файла в S3
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
                        result = add_schedule_data(schedule_data)
                except Exception as e:
                    return Response({'error': f'Ошибка обработки файла {file.name}: {str(e)}'}, status=500)

                # Формирование URL для загруженного файла
                file_url = f"{settings.AWS_END_POINT}/{settings.AWS_BUCKET}/{unique_name}"

                # # Добавление записи о файле в БД (если нужно)
                FileSchedule.objects.create(file_name=file.name, file_url=file_url)

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

from django.db import transaction


# import logging
#
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)


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
                print(group)

                for subgroup_code, subgroup_data in group_data['subgroup'].items():
                    # 3. Получаем или создаем подгруппу
                    relations, created_relation = DivisionRelations.objects.get_or_create(
                        name_relations="По количеству людей"
                    )

                    subgroup, created = Subgroup.objects.get_or_create(
                        group=group,
                        name_subgroup=subgroup_code,  # Добавить проверку, если код ноль, то присвоить NULL
                        defaults={'relations': relations}
                    )

                    print(group_data['schedule']['start_schedule'], group_data['schedule']['end_schedule'])
                    # 4. Создаем расписание
                    schedule, created = Schedule.objects.get_or_create(
                        start_schedule=datetime.strptime(group_data['schedule']['start_schedule'], '%d.%m.%Y'),
                        end_schedule=datetime.strptime(group_data['schedule']['end_schedule'], '%d.%m.%Y'),
                        subgroup=subgroup
                    )
                    print(subgroup)
                    # Проходим по каждому дню недели
                    for weekday, lessons in subgroup_data.items():
                        # Проходим по каждому номеру пары
                        for lesson_time, lesson_data in lessons.items():
                            # 5. Проходим по каждому занятию
                            for lesson_repetition, lesson_info in lesson_data.items():

                                # 5.1 Получаем или создаем преподавателя
                                print(lesson_info)
                                parts = lesson_info['professor_id'].split()

                                if len(parts) > 1:  # Если есть хотя бы фамилия и инициалы
                                    last_name, first_name_and_patronymic = parts[0], parts[1]
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
                                else:
                                    # Если строка содержит только одно слово, значит, это не ФИО
                                    professor = Professor.objects.get_or_create(
                                        last_name='Добавить ФИО преподавателя',
                                        first_name=' ',
                                        patronymic=' ',
                                        post="Неизвестно",
                                        department_id=1
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

                                print(number_lesson, day_of_week, campus, audience, discipline, type, repetition,
                                      professor)

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
