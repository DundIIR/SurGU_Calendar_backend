import os
import boto3
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from urllib.parse import unquote
from .authentication import IsAdminUserRole
from .create_json import create_json
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
        groups = Group.objects.all()
        data = {}

        for group in groups:
            subgroups = Subgroup.objects.filter(group=group).values_list('name_subgroup', flat=True)
            data[group.number_group] = list(subgroups)

        return Response(data)


# Контроллер для получения списка всех преподавателей
class ProfessorsList(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        professors = Professor.objects.all()
        full_names = [f"{prof.last_name} {prof.first_name} {prof.patronymic}" for prof in professors]
        return Response(full_names)


# Проверка авторизации пользователя
class ProtectedDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response({
            'user': serializer.data
        })


## С РЕГИСТРАЦИЕЙ


# Контроллер для получения расписания НОВЫЙ
class ListLessonsAPI(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LessonSerializer

    def get_serializer_context(self):
        # Передаем контекст запроса в сериализатор
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        group = self.request.GET.get('group', '').strip()
        subgroup = self.request.GET.get('subgroup', '').strip()
        professors = self.request.GET.get('professor', '').strip()

        if not group and not professors:
            return Lesson.objects.none()  # Пустой queryset

        return self.search_lessons(group=group, subgroup=subgroup, professors=professors)

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            if not queryset.exists():
                return Response(
                    {
                        "success": False,
                        "error": "Расписание не найдено",
                        "details": "Попробуйте изменить параметры поиска"
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = self.get_serializer(queryset, many=True)

            return Response({
                "success": True,
                "count": len(serializer.data),
                "results": serializer.data
            })

        except Exception as e:
            print(f"Ошибка при получении расписания: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Внутренняя ошибка сервера",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def search_lessons(self, group='', subgroup='', professors=''):

        # Вариант 1: Поиск по профессору
        if professors:
            print('Поиск по профессору')
            parts = professors.split()
            last_name = parts[0] if len(parts) > 0 else ''
            first_name = parts[1] if len(parts) > 1 else ''
            patronymic = parts[2] if len(parts) > 2 else ''

            professor_query = Professor.objects.all()
            if last_name:
                professor_query = professor_query.filter(last_name__icontains=last_name)
            if first_name:
                professor_query = professor_query.filter(first_name__icontains=first_name)
            if patronymic:
                professor_query = professor_query.filter(patronymic__icontains=patronymic)

            professors_found = professor_query.distinct()
            return Lesson.objects.filter(professor__in=professors_found)

        # Вариант 2: Поиск по подгруппе
        elif subgroup and subgroup != '0':
            print('Поиск по подгруппе')
            lessons_subgroup = Lesson.objects.filter(schedule__subgroup__group__number_group=group,
                                                     schedule__subgroup__name_subgroup=subgroup)
            lessons_zero_subgroup = Lesson.objects.filter(schedule__subgroup__group__number_group=group,
                                                          schedule__subgroup__name_subgroup='0')
            return lessons_subgroup.union(lessons_zero_subgroup)
        # Вариант 3: Поиск по группе
        elif group:
            print('Поиск по группе')
            lessons_query = Lesson.objects.filter(schedule__subgroup__group__number_group=group)
            return lessons_query

        return Lesson.objects.none()


# Контроллер для получения файла с расписанием НОВЫЙ
class ScheduleFileView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # Получаем параметры запроса
            group = request.GET.get('group', '').strip()
            subgroup = request.GET.get('subgroup', '').strip()
            professor = request.GET.get('professor', '').strip()
            shorten_names = request.GET.get('shorten_names', 'false').lower() == 'true'

            # Проверяем валидность параметров
            if not any([group, professor]):
                return Response(
                    {"success": False, "error": "Необходимо указать group или professor"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if professor and (group or subgroup):
                return Response(
                    {"success": False, "error": "Параметры group/subgroup не должны указываться вместе с professor"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if professor:
                professor_obj = self.get_professor(professor)
                if not professor_obj:
                    return Response(
                        {"success": False, "error": "Преподаватель не найден", "details": "Ошибка при получении преподавателя"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                # Проверяем есть ли уже файл у профессора
                if professor_obj.file and professor_obj.file.file_url:
                    return Response({
                        "success": True,
                        "results": professor_obj.file.file_url,
                        "from_cache": True
                    })
                lessons = Lesson.objects.filter(professor=professor_obj)
                filename = f"schedule_{professor_obj.last_name}_{professor_obj.first_name}_{professor_obj.patronymic}.ics"
            else:
                # 1. Получаем группу
                group_obj = Group.objects.filter(number_group=group).first()
                if not group_obj:
                    return Response(
                        {"success": False, "error": "Группа не найдена", "details": "Ошибка при получении группы"},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # 2. Получаем все подгруппы этой группы
                all_subgroups = Subgroup.objects.filter(group=group_obj)

                if subgroup and subgroup != '0':
                    # 3. Получаем выбранную подгруппу
                    subgroup_obj = all_subgroups.filter(name_subgroup=subgroup).first()
                    if not subgroup_obj:
                        return Response(
                            {"success": False, "error": "Подгруппа не найдена", "details": "Ошибка при получении подгруппы"},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    # 4.1 Берём только выбранную подгруппу + "0"
                    selected_subgroups = all_subgroups.filter(
                        Q(name_subgroup="0") | Q(id=subgroup_obj.id)
                    )
                else:
                    # 4.2 Если подгруппа не выбрана, берём все подгруппы группы
                    selected_subgroups = all_subgroups
                    subgroup_obj = all_subgroups.filter(name_subgroup="0").first()
                    if not subgroup_obj:
                        return Response(
                            {"success": False, "error": "Общая подгруппа не найдена", "details": "Ошибка при получении общей подгруппы"},
                            status=status.HTTP_404_NOT_FOUND
                        )

                # 5. Берем все необходимые расписания (для 0 -> 0, А, Б)
                schedules = Schedule.objects.filter(subgroup__in=selected_subgroups)

                # 6. Определяем главное расписание исходя из запроса
                # schedule = next((s for s in schedules if s.subgroup == subgroup), None)
                schedule = schedules.filter(subgroup=subgroup_obj).first()

                if not schedule:
                    return Response(
                        {"success": False, "error": "Расписание не найдено", "details": "Ошибка при определении главного расписания"},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # 7. Проверяем есть ли файл у этого расписания
                if schedule and schedule.file is not None:
                    return Response({
                        "success": True,
                        "results": schedule.file.file_url,
                        "from_cache": True,
                    })

                # 8. Получаем занятия для всех найденных расписаний
                filename = f"schedule_{group_obj.number_group}_{subgroup_obj.name_subgroup}.ics"
                lessons = Lesson.objects.filter(schedule__in=schedules).distinct()

            if not lessons.exists():
                return Response(
                    {"success": False, "error": "Нет занятий для создания расписания", "details": "Ошибка при получении занятий"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 9. Создаем файл на основе данных из create_json
            file_path = self.create_ics_file(lessons, subgroup, filename)
            file_url = self.upload_to_s3(file_path)

            # 10. Удаляем файл из media, если загрузка в S3 успешна
            if os.path.exists(file_path):
                os.remove(file_path)

            # 11. Сохраняем ссылку на файл в базе данных
            new_file = FileSchedule(file_name=filename, file_url=file_url)
            new_file.save()

            if professor and professor_obj:
                professor_obj.file = new_file
                professor_obj.save()
            elif group and schedule:
                schedule.file = new_file
                schedule.save()
            else:
                return Response(
                    {"success": False, "error": "Расписание не найдено", "details": "Ошибка на сохранении ссылки"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 12. Отправляем файл пользователю
            return Response({
                "success": True,
                "results": file_url,
                "from_cache": False
            })
        except Exception as e:
            print(f"Ошибка при запросе файла расписания: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Внутренняя ошибка сервера",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_ics_file(self, lessons, subgroup, filename):
        """Создает файл .ics на основе данных из create_json"""
        base_path = os.path.join(settings.STATIC_ROOT, "file", "base.txt")
        events = []

        # Читаем базовый шаблон
        with open(base_path, 'r', encoding='utf-8') as file:
            base_content = file.readlines()

        # Генерируем события для каждого урока
        for lesson in lessons:
            lesson_data = create_json(lesson, True)

            # Формируем правило повторения
            rrule = f"FREQ=WEEKLY;UNTIL={lesson_data['repetition']}"
            if lesson_data['interval']:
                rrule += f";INTERVAL={lesson_data['interval']}"

            # Инициализируем description
            description = lesson_data.get('description', '')  # Безопасное получение описания

            # Формируем description по условиям
            if not subgroup:
                description += ('\n\n' if description else '') + lesson_data.get('group', '') + (str(lesson_data.get('subgroup', '')) if lesson_data.get('subgroup', '0') != '0' else '')
            else:
                description = lesson_data.get('professor', '') + ('\n\n' if description else '') + description
                if subgroup == '0':
                    description += ('\n\n' if description else '') + (
                        lesson_data.get('group', '') + str(lesson_data.get('subgroup', ''))
                        if lesson_data.get('subgroup', '0') != '0' else 'общая'
                    )

            event = (
                "BEGIN:VEVENT\n"
                f"DTSTART:{lesson_data['datetime_start_lesson']}\n"
                f"DTEND:{lesson_data['datetime_end_lesson']}\n"
                f"RRULE:{rrule}\n"
                f"CREATED:{lesson_data['create']}\n"
                f"DESCRIPTION:{description.strip().replace('\n', r'\n')}" + '\n'
                f"LOCATION:{lesson_data['location']}\n"
                f"SUMMARY:{lesson_data['summary']}\n"
                "END:VEVENT\n"
            )
            print(event)
            events.append(event)

        # Вставляем события перед `END:VCALENDAR`
        insert_index = base_content.index("END:VCALENDAR")
        final_content = base_content[:insert_index] + events + [base_content[insert_index]]

        # Сохраняем во временный файл
        file_path = os.path.join(settings.MEDIA_ROOT, "schedule", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Записываем в файл
        with open(file_path, 'w', encoding='utf-8') as ics_file:
            ics_file.write("".join(final_content))

        return file_path

    def upload_to_s3(self, file_path):
        """Загружает файл в S3 хранилище"""
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_END_POINT,
            region_name=settings.AWS_REGION,
        )

        # Создаем уникальное имя для файла
        unique_name = os.path.basename(file_path)

        # Загружаем файл в S3
        with open(file_path, 'rb') as file:
            s3_client.upload_fileobj(
                Fileobj=file,
                Bucket=settings.AWS_BUCKET,
                Key=f'icl/{unique_name}',
                ExtraArgs={'ContentType': 'text/calendar'}
            )

        # Возвращаем URL файла
        file_url = f"{settings.AWS_END_POINT}/{settings.AWS_BUCKET}/icl/{unique_name}"
        file_url = file_url.replace("http://", "https://")
        return file_url

    def get_professor(self, professor):
        # Поиск по профессору
        parts = professor.split()
        last_name = parts[0] if len(parts) > 0 else ''
        first_name = parts[1] if len(parts) > 1 else ''
        patronymic = parts[2] if len(parts) > 2 else ''

        professor_query = Professor.objects.all()
        if last_name:
            professor_query = professor_query.filter(last_name__icontains=last_name)
        if first_name:
            professor_query = professor_query.filter(first_name__icontains=first_name)
        if patronymic:
            professor_query = professor_query.filter(patronymic__icontains=patronymic)

        return professor_query.first()



# def search_lessons(self, attr1, attr2=None, attr3=None):
#     print('Составляем расписание')
#     if attr3:
#         search_results = Professor.objects.get(last_name=attr1, first_name=attr2, patronymic=attr3)
#         lessons = Lesson.objects.filter(professor=search_results)
#     elif attr2:
#         lessons1 = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1,
#                                          schedule__subgroup__name_subgroup=attr2)
#         lessons2 = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1,
#                                          schedule__subgroup__name_subgroup='0')
#         lessons = lessons1.union(lessons2)
#     else:
#         lessons = Lesson.objects.filter(schedule__subgroup__group__number_group=attr1)
#         print(lessons, attr1)
#     return lessons




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


# class ScheduleFileView(APIView):
#     authentication_classes = []
#     permission_classes = [AllowAny]
#
#     def get(self, request):
#         search = request.query_params.get('search', '')
#         subgroup_name = request.query_params.get('subgroup', None)
#         professor = request.query_params.get('professor', 'false').lower() == 'true'
#
#         if not search:
#             return Response({"message": "Поле 'search' обязательно"}, status=400)
#
#         if professor:
#             professor = self.get_professor(search)
#             if not professor:
#                 return Response({"message": "Преподаватель не найден"}, status=404)
#             schedule = Lesson.objects.filter(professor=professor)
#             filename = f"schedule_{professor.last_name}.ics"
#             schedule_obj = Schedule.objects.filter(professor=professor).first()
#         else:
#             # 1. Получаем группу
#             group = Group.objects.filter(number_group=search).first()
#             if not group:
#                 return Response({"message": "Группа не найдена"}, status=404)
#
#             # 2. Получаем все подгруппы этой группы
#             all_subgroups = Subgroup.objects.filter(group=group)
#
#             if subgroup_name and subgroup_name.lower() != "none":
#                 # 3. Получаем выбранную подгруппу
#                 subgroup = all_subgroups.filter(name_subgroup=subgroup_name).first()
#                 if not subgroup:
#                     return Response({"message": "Подгруппа не найдена"}, status=404)
#                 # 4. Берём только выбранную подгруппу + "0"
#                 selected_subgroups = all_subgroups.filter(Q(name_subgroup="0") | Q(id=subgroup.id))
#             else:
#                 # Если подгруппа не выбрана, берём все подгруппы группы
#                 selected_subgroups = all_subgroups
#                 subgroup = all_subgroups.filter(name_subgroup="0").first()
#                 if not subgroup:
#                     return Response({"message": "Подгруппа не найдена"}, status=404)
#
#             # 5. Берем все необходимые расписания (для 0 -> 0, А, Б)
#             schedules = Schedule.objects.filter(subgroup__in=selected_subgroups)
#
#             # 6. Определяем главное расписание исходя из запроса
#             schedule = next((s for s in schedules if s.subgroup == subgroup), None)
#
#             # 7. Проверяем есть ли файл у этого расписания
#             if schedule.file is not None:
#                 file_url = schedule.file.file_url
#             else:
#                 # 8. Получаем занятия для всех найденных расписаний
#                 lessons = Lesson.objects.filter(schedule__in=schedules).distinct()
#
#                 file_path = self.create_ics_file(subgroup, schedule, lessons)
#                 file_url = self.upload_to_s3(file_path)
#
#                 # Удаляем файл из media, если загрузка в S3 успешна
#                 if os.path.exists(file_path):
#                     os.remove(file_path)
#
#                 # Сохраняем ссылку на файл в базе данных
#                 new_file = FileSchedule(file_name=file_path, file_url=file_url)
#                 new_file.save()
#                 schedule.file = new_file
#                 schedule.save()
#
#                 # 9. Отправляем файл пользователю
#             return Response({"file_url": file_url})
#
#     def create_ics_file(self, subgroup, schedule, lessons):
#         print('Файла нет, создаем свой ', subgroup)
#         list_days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
#         time_zone = 'Asia/Yekaterinburg:'
#
#         base_path = os.path.join(settings.STATIC_ROOT, "file", "base.txt")
#
#         events = []
#
#         start_schedule = schedule.start_schedule
#         end_schedule = schedule.end_schedule
#
#         id_week_of_day = start_schedule.weekday()  # День недели (0 - понедельник, 6 - воскресенье)
#         for lesson in lessons:
#             # Определяем день недели для урока
#             id_week_of_day_lesson = list_days_of_week.index(str(lesson.day))
#
#             # Рассчитываем разницу в днях
#             if id_week_of_day_lesson >= id_week_of_day:
#                 plus_days = id_week_of_day_lesson - id_week_of_day
#                 flag = True
#             else:
#                 plus_days = id_week_of_day_lesson - id_week_of_day + 7
#                 flag = False
#
#
#
#             if str(lesson.repetition).lower() == 'каждую неделю':
#                 date_start_lesson = start_schedule + timedelta(days=plus_days)
#             elif lesson.repetition == 'Числитель' and flag:
#                 date_start_lesson = start_schedule + timedelta(days=plus_days)
#             elif lesson.repetition == 'Знаменатель' and not flag:
#                 date_start_lesson = start_schedule + timedelta(days=plus_days)
#             else:
#                 date_start_lesson = start_schedule + timedelta(days=plus_days + 7)
#
#             # Формируем строки события
#             start_time = time_zone+str(date_start_lesson.strftime('%Y%m%d'))+'T'+str(lesson.time.time_start.strftime('%H%M%S'))
#             end_time = time_zone+str(date_start_lesson.strftime('%Y%m%d'))+'T'+str(lesson.time.time_end.strftime('%H%M%S'))
#
#             # Определяем правило повторения
#             repetition = "FREQ=WEEKLY;UNTIL=" + end_schedule.strftime('%Y%m%d') + 'T235959'
#             if lesson.repetition in ['Числитель', 'Знаменатель']:
#                 repetition += ";INTERVAL=2"
#
#             created = str(datetime.now().strftime('%Y%m%d'))
#
#             description = '<b>' + str(lesson.professor) + '</b><br>'
#
#             location = (("online" if str(lesson.campus).lower() == "эоидот" else str(lesson.campus))
#                         + (str(lesson.audience) if lesson.audience else "")
#                         + ' ' + str(lesson.type))
#
#             event = (
#                 "BEGIN:VEVENT\n"
#                 f"DTSTART;TZID={start_time}\n"
#                 f"DTEND;TZID={end_time}\n"
#                 f"RRULE:{repetition}\n"
#                 f"CREATED:{created}\n"
#                 f"DESCRIPTION:{description}\n"
#                 f"LOCATION:{location}\n"
#                 f"SUMMARY:{lesson.discipline}\n"
#                 "END:VEVENT\n"
#             )
#             events.append(event)
#
#         # Читаем base.txt
#         with open(base_path, 'r', encoding='utf-8') as file:
#             base_content = file.readlines()
#
#         # Вставляем события перед `END:VCALENDAR`
#         insert_index = base_content.index("END:VCALENDAR")
#         final_content = base_content[:insert_index] + events + [base_content[insert_index]]
#
#         # Определяем путь сохранения
#         file_name = f"schedule_{subgroup.group}_{subgroup.name_subgroup}.ics"
#         file_path = os.path.join(settings.MEDIA_ROOT, "schedule", file_name)
#
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#
#         # Записываем в файл
#         with open(file_path, 'w', encoding='utf-8') as ics_file:
#             ics_file.write("".join(final_content))
#
#         return file_path
#
#     def upload_to_s3(self, file_path):
#         # Создаем клиента для S3
#         s3_client = boto3.client(
#             's3',
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             endpoint_url=settings.AWS_END_POINT,
#             region_name=settings.AWS_REGION,
#         )
#
#         # Создаем уникальное имя для файла
#         unique_name = f"{os.path.basename(file_path)}"
#
#         # Загружаем файл в S3
#         with open(file_path, 'rb') as file:
#             s3_client.upload_fileobj(
#                 Fileobj=file,
#                 Bucket=settings.AWS_BUCKET,
#                 Key=f'icl/{unique_name}',
#                 ExtraArgs={'ContentType': 'text/calendar'}
#             )
#
#         # Возвращаем URL файла
#         file_url = f"{settings.AWS_END_POINT}/{settings.AWS_BUCKET}/icl/{unique_name}"
#         file_url = file_url.replace("http://", "https://")
#         return file_url
#
#     def get_professor(self, search):
#         parts = search.split()
#         if len(parts) == 1:
#             return Professor.objects.filter(last_name__icontains=parts[0]).first()
#         elif len(parts) == 2:
#             return Professor.objects.filter(last_name__icontains=parts[0], first_name__icontains=parts[1]).first()
#         elif len(parts) == 3:
#             return Professor.objects.filter(last_name=parts[0], first_name=parts[1], patronymic=parts[2]).first()
#         return None
#

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
                return None
        return None

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






class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]


class UpdateUserRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
