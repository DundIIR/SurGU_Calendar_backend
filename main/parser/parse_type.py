import re
from typing import Tuple


def extract_type(input_str: str, type_abbreviations: dict) -> Tuple[str, str]:
    """
                Разбивает строку на две части:\n
                - `before`: оставшаяся часть строки
                - `type`: тип занятия
    """
    start = input_str.rfind('(')
    end = input_str.rfind(')')

    temp = input_str[start + 1:end].strip() if start != -1 and end != -1 else 'занятие'
    for key, value in type_abbreviations.items():
        if key in temp:
            tt = value
            break
    else:
        tt = 'занятие'
    input_str = input_str[:start].strip() if start != -1 else input_str.strip()

    if '/' in input_str:
        start = input_str.rfind('(')
        end = input_str.rfind(')')
        temp = input_str[start + 1:end].strip() if start != -1 and end != -1 else 'занятие'
        tt = type_abbreviations.get(temp, 'занятие') + '/' + tt
        input_str = input_str[:start].strip() if start != -1 else input_str.strip()

    return input_str, tt


if __name__ == "__main__":
    type_abb = {
        'пр': 'практика',
        'лек': 'лекция',
        'лаб': 'лаба',
        'CDIO': 'CDIO',
    }
    inputs = [
        'Экономика физической культуры и спорта (пр)',
        'Иностранный язык в профессиональной сфере (24ч)',
        'Экономика физической культуры и спорта (пр)/(лек)',
        'Волейбол с методикой преподавания',
        'Научные исследования в сфере физической культуры и спорта (лек)/(пр)',
        'День самостоятельной работы',
        'Спортивно-педагогические дисциплины (пр28 ч)',
        'Базы данных (CDIO)'
    ]

    for str_ in inputs:
        before, type_ = extract_type(str_, type_abb)
        print("Input:", str_)
        print("Before:", before)
        print("type:", type_)
        print()