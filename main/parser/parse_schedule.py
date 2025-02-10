import os
import re
import json
from pdfplumber import open as pdf_open
from PyPDF2 import PdfReader
from .parse_type import extract_type
from .parse_campus_audience import extract_campus_audience


def parse_schedule_data(schedule_data, schedule_dict, type_campus, type_subgroup, type_abbreviations, professors):
    """
    Разбирает данные о расписания из массива строк и обновляет словарь с расписанием.

    Аргументы:
    schedule_data (list): Данные расписания в виде списка строк (полученные данные из одной страницы PDF файла).
    schedule_dict (dict): Словарь для хранения информации о расписании.
    type_campus (list): Список типов кампусов.
    type_subgroup (list): Список подгрупп.
    type_abbreviations (dict): Словарь сокращений типов занятий.
    professors (dict): Словарь с информацией о преподавателях.

    Возвращает:
    dict: Обновлённый словарь с добавленной информацией о расписании.
    """
    group_number, name_speciality, cod_speciality = '', '', ''
    day = 'None'  # День недели (по умолчанию отсутствует)
    try:
        # Итерация по строкам данных расписания
        for index, row in enumerate(schedule_data):
            # Обработка первой строки — извлечение информации о специальности и группе
            if index == 0:
                group_info = row[2].replace('\n', ' ')

                # Извлечение кода специальности
                pattern = r'\d+\.\d+\.\d+'
                match = re.search(pattern, group_info)
                if match:
                    cod_speciality = match.group()
                    end_index = match.end() + 1
                    group_info = group_info[end_index:]
                else:
                    raise ValueError("Не удалось найти код специальности")

                # Извлечение номера группы
                pattern = r'\d{3}-\d{2}м?'
                match = re.search(pattern, group_info)
                if match:
                    group_number = match.group()
                else:
                    raise ValueError("Не удалось найти номер группы")

                # Добавление специальности и группы в словарь
                if cod_speciality not in schedule_dict:
                    name_speciality = re.sub(group_number, '', group_info).rstrip()
                    schedule_dict[cod_speciality] = {
                        'name_speciality': name_speciality,
                        'groups': {}
                    }
                if group_number not in schedule_dict[cod_speciality]['groups']:
                    schedule_dict[cod_speciality]['groups'][group_number] = {
                        'schedule': {},
                        'subgroup': {"0": {}}
                    }

            # Обработка второй строки — извлечение диапазона дат расписания
            elif index == 1:
                group_info = row[2].replace('\n', '')
                pattern = r'\d{2}\.\d{2}\.\d{4}-\d{2}\.\d{2}\.\d{4}'
                match = re.search(pattern, group_info)
                if match:
                    date_range = match.group().split('-')
                    start_schedule = date_range[0]
                    end_schedule = date_range[1]
                else:
                    start_schedule = '03.02.2025'
                    end_schedule = '31.06.2025'

                # Добавление диапазона дат в словарь
                schedule_dict[cod_speciality]['groups'][group_number]['schedule'] = {
                    'start_schedule': start_schedule,
                    'end_schedule': end_schedule
                }

            # Обработка строк с занятиями
            elif row[1].isdigit() or re.match(r'^\d-\d', row[1]):

                if row[0] != '':
                    day = row[0]  # Обновляем текущий день недели

                # Номер занятия
                if row[1].isdigit():
                    lesson_number = row[1]
                else:
                    lesson_number = row[1][0]

                # Обработка информации о каждом занятии
                for index_lesson, lesson_info in enumerate(row[2:], start=1):
                    if not lesson_info or 'день самостоятельной работы' in lesson_info.lower():
                        continue

                    # Разбиение строки занятия
                    li = lesson_info.replace('\n', ' ').replace('.', ',').split('//')

                    is_shared_campus = False

                    for i, item in enumerate(li):
                        if not item:
                            continue

                        # Определение повторяемости (чётная, нечётная или каждая неделя)
                        repetition = 'ч' if len(li) > 1 and i == 0 else 'з' if len(li) > 1 else 'кн'

                        # Извлечение кампуса и аудитории
                        data, campus, audience = extract_campus_audience(item, type_campus)
                        if (campus == 'None' or campus == '') and len(li) > 1:
                            d, campus, a = extract_campus_audience(li[-1], type_campus)
                            if campus in ['C', 'С']:
                                is_shared_campus = True

                        if audience == '*':
                            audience = ''

                        # Определение подгруппы
                        subgroup = type_subgroup[index_lesson] if 'п/г' in data else type_subgroup[0]
                        end = data.find('п/г') if 'п/г' in data else None
                        data = data[:end] if end else data

                        # Извлечение типа занятия
                        data, type_lesson = extract_type(data, type_abbreviations)
                        discipline = data.strip().rstrip(',').replace(',', '.')

                        # Формирование ключа преподавателя
                        professor_key = f'{day}_'

                        rep = '//'
                        if is_shared_campus:
                            rep = ''

                        subgroup_part = "" if subgroup == "0" else subgroup

                        if repetition == 'ч':
                            professor_key += f'{group_number}{subgroup_part}{rep}_{lesson_number}'
                        elif repetition == 'з':
                            professor_key += f'{rep}{group_number}{subgroup_part}_{lesson_number}'
                        else:
                            professor_key += f'{group_number}{subgroup_part}_{lesson_number}'

                        professor_data = professors.get(professor_key)
                        professor_id = professor_data[0] if professor_data else professor_key

                        # Добавление данных в словарь
                        subgroup_dict = schedule_dict[cod_speciality]['groups'][group_number]['subgroup']
                        if subgroup not in subgroup_dict:
                            subgroup_dict[subgroup] = {}
                        if day not in subgroup_dict[subgroup]:
                            subgroup_dict[subgroup][day] = {}
                        if lesson_number not in subgroup_dict[subgroup][day]:
                            subgroup_dict[subgroup][day][lesson_number] = {}

                        # Сохранение данных о занятии
                        subgroup_dict[subgroup][day][lesson_number][repetition] = {
                            'campus_id': campus,
                            'audience_id': audience,
                            'discipline_id': discipline,
                            'type_id': type_lesson,
                            'professor_id': professor_id,
                        }

        return schedule_dict

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return {}


# Функция для загрузки данных из JSON
def load_professors_from_json(json_path):
    try:
        print('Парсер: начало загрузки файла занятости')
        print(os.path.isfile(json_path))
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Парсер: данные о зянятости получены")
        return data
    except FileNotFoundError:
        print(f"Парсер: файл занятости не найден.", json_path)
        return {}
    except json.JSONDecodeError as e:
        print(f"Парсер: ошибка декодирования JSON: {e}")
        return {}
    except Exception as e:
        print(f"Парсер: произошла ошибка при загрузке занятости: {e}")
        return {}



def process_schedule(path_pdf, type_campus, type_subgroup, type_abbreviations, specific_page=None, page_range=None, json_path='other_files\\professor_availability.json'):
    """
    Обрабатывает PDF-файл с расписанием из потока и возвращает словарь расписания.

    Аргументы:
    path_pdf (BytesIO): Байтовый поток с содержимым PDF-файла.
    json_path (str): Путь к JSON-файлу с данными о преподавателях.
    type_campus (list): Список типов кампусов.
    type_subgroup (list): Список подгрупп.
    type_abbreviations (dict): Словарь сокращений типов занятий.
    specific_page (int, optional): Номер страницы для обработки (если None, обрабатываются все страницы).
    page_range (tuple, optional): Диапазон страниц для обработки (start, end). Если указан, specific_page игнорируется.

    Возвращает:
    dict: Словарь с данными расписания.
    """
    try:
        # Загрузка данных о преподавателях
        with open(json_path, 'r', encoding='utf-8') as f:
            professors = json.load(f)

        # Инициализация словаря для расписания
        schedule_dict = {'key': 'okey'}

        # Использование pdfplumber для работы с файлом
        with pdf_open(path_pdf) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                # Проверяем, нужно ли обрабатывать только определённую страницу
                if page_range:
                    start, end = page_range
                    if page_number < start or page_number > end:
                        continue
                elif specific_page and page_number != specific_page:
                    continue

                try:
                    # Извлечение текста или таблицы со страницы
                    schedule_data = page.extract_table()

                    if schedule_data:
                        print(f"Парсер: обработка страницы {page_number}")
                        # schedule_dict = parse_schedule_data(
                        #     schedule_data,
                        #     schedule_dict,
                        #     type_campus,
                        #     type_subgroup,
                        #     type_abbreviations,
                        #     professors
                        # )
                    else:
                        print(f"Парсер: на странице {page_number} нет данных.")
                except Exception as e:
                    print(f"Парсер: ошибка на странице {page_number}: {e}")

        return schedule_dict

    except Exception as e:
        print(f"Парсер: произошла ошибка при обработке расписания: {e}")
        return {}


if __name__ == '__main__':
    # 1 в каждой переменной, чтобы убрать ошибку повтора глобальных переменных

    # Параметры
    type_campus1 = ['ЭОиДОТ', 'С']
    type_subgroup1 = ['0', 'а', 'б', 'в', 'г']
    type_abbreviations1 = {
        'пр': 'практика',
        'лек': 'лекция',
        'лаб': 'лаба',
        'CDIO': 'CDIO'
    }
    path_pdf1 = '../../other_files/Programmnaya inzheneriya-15-01-25.pdf'
    json_path1 = '../../other_files/professor_availability.json'
    specific_page1 = 7

    # Вызов функции
    result = process_schedule(path_pdf1, json_path1, type_campus1, type_subgroup1, type_abbreviations1, specific_page1)

    # Вывод результата
    print(result)
