from datetime import datetime, timedelta

list_days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']


def create_json(instance):
    result = []
    schedules = instance.schedule.all()

    for schedule in schedules:
        json_data = {
            'datetime_start_lesson': None,
            'datetime_end_lesson': None,
            'repetition': None,
            'interval': None,
            'create': datetime.now().strftime('%Y%m%d'),
            'location': '',
            'summary': '',
            'description': '',
            'subgroup': ''
        }

        try:
            # Обработка даты и времени
            id_week_of_day = schedule.start_schedule.weekday()
            id_week_of_day_lesson = list_days_of_week.index(str(instance.day))

            if id_week_of_day_lesson >= id_week_of_day:
                plus_days = id_week_of_day_lesson - id_week_of_day
                flag = True
            else:
                plus_days = id_week_of_day_lesson - id_week_of_day + 7
                flag = False

            if str(instance.repetition) in ['Числитель', 'Каждую неделю'] and flag:
                date_start_lesson = schedule.start_schedule + timedelta(days=plus_days)
            elif str(instance.repetition) in ['Знаменатель', 'Каждую неделю'] and not flag:
                date_start_lesson = schedule.start_schedule + timedelta(days=plus_days)
            else:
                date_start_lesson = schedule.start_schedule + timedelta(days=plus_days + 7)

            # Форматирование даты и времени
            date_str = date_start_lesson.strftime('%Y%m%d')
            time_start_str = instance.time.time_start.strftime('%H%M%S') if instance.time else '000000'
            time_end_str = instance.time.time_end.strftime('%H%M%S') if instance.time else '000000'

            json_data['datetime_start_lesson'] = f"{date_str}T{time_start_str}"
            json_data['datetime_end_lesson'] = f"{date_str}T{time_end_str}"
            json_data[
                'repetition'] = f"{schedule.end_schedule.strftime('%Y%m%d')}T235959Z" if schedule.end_schedule else None

            # Обработка повторений
            repetition_map = {
                'Числитель': '2',
                'Знаменатель': '2',
                'Каждую неделю': ''
            }
            json_data['interval'] = repetition_map.get(str(instance.repetition), None)

            # Формирование location
            campus = getattr(instance.campus, 'reduction', 'online').lower()
            campus = 'online' if campus == 'эоидот' else campus
            audience_num = getattr(getattr(instance, 'audience', None), 'number_audience', '')
            type_name = getattr(getattr(instance, 'type', None), 'name_type', '')
            json_data['location'] = f"{campus}{audience_num} {type_name}".strip()

            # Формирование summary (инициалы дисциплины)
            name_discipline = getattr(getattr(instance, 'discipline', None), 'name_discipline', '')
            if name_discipline:
                initials = []
                for word in name_discipline.split():
                    if len(word) > 1:
                        initials.append(word[0].upper())
                    else:
                        initials.append(word[0].lower())
                json_data['summary'] = ''.join(initials)

            # Формирование description (ФИО преподавателя + название дисциплины)
            professor = instance.professor
            if professor:
                professor_name = f"{professor.last_name} {professor.first_name} {professor.patronymic}".strip()
                json_data['description'] = f"{professor_name}\n\n{name_discipline}".strip()
            else:
                json_data['description'] = name_discipline

            # Формирование subgroup
            subgroup = schedule.subgroup
            if subgroup:
                group_num = getattr(subgroup.group, 'number_group', '')
                subgroup_name = getattr(subgroup, 'name_subgroup', '')
                json_data['subgroup'] = f"{group_num}{subgroup_name}" if subgroup_name else group_num

            result.append(json_data)

        except Exception as e:
            # Логирование ошибки, если нужно
            continue

    return result[0] if result else {}


# def create_json(instance):
#     json = dict()
#     schedules = instance.schedule.all()
#     for schedule in schedules:
#         id_week_of_day = schedule.start_schedule.weekday()
#         id_week_of_day_lesson = list_days_of_week.index(str(instance.day))
#         if id_week_of_day_lesson >= id_week_of_day:
#             plus_days = id_week_of_day_lesson - id_week_of_day
#             flag = True
#         else:
#             plus_days = id_week_of_day_lesson - id_week_of_day + 7
#             flag = False
#
#         if str(instance.repetition) in ['Числитель', 'Каждую неделю'] and flag:
#             date_start_lesson = schedule.start_schedule + timedelta(days=plus_days)
#         elif str(instance.repetition) in ['Знаменатель', 'Каждую неделю'] and not flag:
#             date_start_lesson = schedule.start_schedule + timedelta(days=plus_days)
#         else:
#             date_start_lesson = schedule.start_schedule + timedelta(days=plus_days + 7)
#
#         repetition = ''
#         if str(instance.repetition) in ['Числитель', 'Знаменатель']:
#             repetition = '2'
#
#         json['datetime_start_lesson'] = (str(date_start_lesson.strftime('%Y%m%d')) +
#                                          'T' + str(instance.time.time_start.strftime('%H%M%S')))
#         json['datetime_end_lesson'] = (str(date_start_lesson.strftime('%Y%m%d')) +
#                                        'T' + str(instance.time.time_end.strftime('%H%M%S')))
#         json['repetition'] = str(schedule.end_schedule.strftime('%Y%m%d')) + 'T235959Z'
#         json['interval'] = repetition
#         json['create'] = str(datetime.now().strftime('%Y%m%d'))
#
#         # Проверка number_audience на None
#         campus = instance.campus.reduction
#         campus = campus if campus.lower() != 'эоидот' else 'online'
#         json['location'] = (campus +
#                             (instance.audience.number_audience if instance.audience and instance.audience.number_audience else '') +
#                             ' ' + instance.type.name_type)
#
#         name_discipline = instance.discipline.name_discipline
#         json['summary'] = ''.join([word[0].upper() if len(word) > 1 else word[0].lower() for word in name_discipline.split()])
#         json['description'] = (f"{instance.professor.last_name} {instance.professor.first_name} "
#                                f"{instance.professor.patronymic}\n\n{name_discipline}")
#         if schedule.subgroup.name_subgroup:
#             json['subgroup'] = f"{schedule.subgroup.group.number_group}{schedule.subgroup.name_subgroup}"
#         else:
#             json['subgroup'] = f"{schedule.subgroup.group.number_group}"
#     return json
