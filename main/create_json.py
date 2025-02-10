from datetime import datetime, timedelta

list_days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']


def create_json(instance):
    json = dict()
    schedules = instance.schedule.all()
    for schedule in schedules:
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

        repetition = ''
        if str(instance.repetition) in ['Числитель', 'Знаменатель']:
            repetition = '2'

        json['datetime_start_lesson'] = (str(date_start_lesson.strftime('%Y%m%d')) +
                                         'T' + str(instance.time.time_start.strftime('%H%M%S')))
        json['datetime_end_lesson'] = (str(date_start_lesson.strftime('%Y%m%d')) +
                                       'T' + str(instance.time.time_end.strftime('%H%M%S')))
        json['repetition'] = str(schedule.end_schedule.strftime('%Y%m%d')) + 'T235959Z'
        json['interval'] = repetition
        json['create'] = str(datetime.now().strftime('%Y%m%d'))

        # Проверка number_audience на None
        campus = instance.campus.reduction
        campus = campus if campus.lower() != 'эоидот' else 'online'
        json['location'] = (campus +
                            (instance.audience.number_audience if instance.audience and instance.audience.number_audience else '') +
                            ' ' + instance.type.name_type)

        name_discipline = instance.discipline.name_discipline
        json['summary'] = ''.join([word[0].upper() if len(word) > 1 else word[0].lower() for word in name_discipline.split()])
        json['description'] = (f"{instance.professor.last_name} {instance.professor.first_name} "
                               f"{instance.professor.patronymic}\n\n{name_discipline}")
        if schedule.subgroup.name_subgroup:
            json['subgroup'] = f"{schedule.subgroup.group.number_group}{schedule.subgroup.name_subgroup}"
        else:
            json['subgroup'] = f"{schedule.subgroup.group.number_group}"
    return json
