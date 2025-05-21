from datetime import datetime, timedelta

list_days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']

def should_shorten_word(word):
    """Определяет, нужно ли сокращать слово"""
    # Не сокращаем двухбуквенные слова
    if len(word) <= 2:
        return False

    if word.upper() == "ФТД:":
        return False

    if 'IT' in word.upper():
        return False

    return True


def create_short_name(full_name):
    """Создает сокращенное название по правилам"""
    words = full_name.split()

    # Если название из одного слова - не сокращаем
    if len(words) == 1:
        return full_name

    # Если из двух слов - проверяем длину каждого
    if len(words) == 2:
        word1, word2 = words
        # Сокращаем только если оба слова подлежат сокращению
        if should_shorten_word(word1) and should_shorten_word(word2):
            return f"{word1[0].upper()}{word2[0].upper()}"
        return full_name

    # Для трех и более слов применяем общее правило
    initials = []
    for word in words:
        if should_shorten_word(word):
            initials.append(word[0].upper())
        else:
            initials.append(word)

    # Собираем результат, убирая лишние пробелы
    return ''.join(initials)

def create_json(instance, shorten_names=True):
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
            'professor': '',
            'group': '',
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

            # Формирование summary (полное название дисциплины)
            name_discipline = getattr(getattr(instance, 'discipline', None), 'name_discipline', '')
            if name_discipline:
                if shorten_names:
                    json_data['summary'] = create_short_name(name_discipline)
                else:
                    json_data['summary'] = name_discipline

            # Формирование description (ФИО преподавателя + полное название дисциплины, если сокращали его)
            if shorten_names and name_discipline:
                # Добавляем полное название через два переноса строки
                json_data['description'] = f"{name_discipline}"

            professor = instance.professor
            if professor:
                json_data['professor'] = f"{professor.last_name} {professor.first_name} {professor.patronymic}".strip()

            # Формирование group и subgroup (раздельно)
            subgroup = schedule.subgroup
            if subgroup:
                group_num = getattr(subgroup.group, 'number_group', '')
                subgroup_name = getattr(subgroup, 'name_subgroup', '')

                # Отдельное поле для номера группы
                json_data['group'] = group_num

                # Отдельное поле для названия подгруппы (если есть)
                json_data['subgroup'] = subgroup_name if subgroup_name else ""
            else:
                json_data['group'] = ""
                json_data['subgroup'] = ""

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
