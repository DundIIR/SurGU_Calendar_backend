from django.core.management.base import BaseCommand
from main.models import *


class Command(BaseCommand):
    help = 'Добавление данных в расписание'

    def handle(self, *args, **kwargs):
        data = {
            '09.03.04': {
                'name_speciality': 'Программная инженерия',
                'groups': {
                    '609-11': {
                        'schedule': {
                            'start_schedule': '03.02.2025',
                            'end_schedule': '08.04.2025'
                        },
                        'subgroup': {
                            '0': {
                                'пн': {
                                    '2': {
                                        'кН': {
                                            'campus_id': 'ЭОиДОТ',
                                            'audience_id': '',
                                            'discipline_id': 'сИстЕмы управлЕния базами данных',
                                            'type_id': 'лекция',
                                            'professor_id': 'Кузин Д.А.',
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # Вызываем функцию добавления данных
        result = add_schedule_data(data)
        print('Данные добавлены в БД')


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