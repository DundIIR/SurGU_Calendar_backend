import openpyxl
import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings

# Функция для извлечения данных из Excel
def extract_professor(file_path: str) -> dict:
    day_of_week = {3: 'ПН', 5: 'ВТ', 7: 'СР', 9: 'ЧТ', 11: 'ПТ', 13: 'СБ'}
    inf = 0
    professors = {}
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        for row in sheet.iter_rows(values_only=True):
            if inf == 0:
                inf += 1
                continue
            else:
                FIO = row[0]
                departament = row[1]
                for i in range(3, 14, 2):
                    if row[i] is not None and '--' not in row[i]:
                        groups = split_group(row[i])
                        for group in groups:
                            key = f'{day_of_week[i]}_{group}_{int(row[2])}'
                            professors[key] = [FIO, int(departament)]
        return professors
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
        return professors
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return professors
    finally:
        if 'workbook' in locals():
            workbook.close()

# Функция для разделения групп
def split_group(input_str: str) -> list:
    input_str = input_str.replace(' ', '')
    list = []
    if '/' in input_str:
        if '//' in input_str:
            input_str = input_str.split('//')
        else:
            input_str = input_str.split('/')
        for i, item in enumerate(input_str):
            if not item: continue
            item = item.split(',')
            for group in item:
                if i == 0:
                    list.append(group+'//')
                else:
                    list.append('//' + group)
        return list
    elif sum(1 for char in input_str if char.isalpha() and char != 'м') > 1:
        item = input_str.split(',')
        for group in item:
            part = []
            temp = ''
            for char in group:
                if char.isalpha():
                    part.append(char)
                else:
                    temp += char
            list.append(f'{temp}{part[0]}//')
            list.append(f'//{temp}{part[1]}')
        return list
    else:
        return input_str.split(',')

# Функция для сохранения данных в JSON
def save_to_json(data: dict, filename: str, xlsx_file_path: str):
    dir_path = os.path.dirname(xlsx_file_path)

    file_path = os.path.join(dir_path, filename)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Файл успешно сохранен в {file_path}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")


class Command(BaseCommand):
    help = 'Извлекает данные о занятости преподавателей из Excel и сохраняет в JSON файл'

    def handle(self, *args, **options):
        # Путь к файлу Excel
        path_xlsx = os.path.join(settings.BASE_DIR, 'other_files', 'Zanyatost.xlsx')

        output_json_path = 'professor_availability.json'

        # Извлечение данных из Excel
        result = extract_professor(path_xlsx)
        # print(result)

        save_to_json(result, output_json_path, path_xlsx)
        print('Данные успешно сохранены в JSON файл.')