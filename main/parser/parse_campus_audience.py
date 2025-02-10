import re
from typing import List, Tuple
def extract_campus_audience(input_str: str, campus_type: List[str]) -> Tuple[str, str, str]:
    """
        Разбивает строку на три части:\n
        - `before`: оставшаяся часть строки
        - `campus`: тип кампуса
        - `audience`: аудитория
    """
    pattern = r'([А-ЯЁ]\d{2})'
    match = re.search(pattern, input_str)
    if match:
        index = match.start()
        before = input_str[:index - 2]
        campus = input_str[index]
        audience = input_str[index+1:]
    else:
        str = input_str.rsplit(',', 1)
        before = str[0].strip()
        audience = str[-1].strip()
        campus = ''
        for item in campus_type:
            if item in audience:
                campus = item
                audience = audience[audience.index(campus)+len(campus):]
                break
    if audience == before:
        audience = ''
    return before.strip(), campus.strip(), audience.strip()


if __name__ == '__main__':

    campus_type = ['ЭОиДОТ', 'C']

    # Тесты
    inputs = [
        'Экономика физической культуры и спорта (пр), К425',
        'Экономика физической культуры и спорта (пр), К425a',
        'Экономика физической культуры и спорта (пр), У42',
        'Экономика физической культуры и спорта (пр), У420,310',
        'Иностранный язык в профессиональной сфере (24ч), п/г 2, А518',
        'Экономика физической культуры и спорта (пр)/(лек), К425',
        'Волейбол с методикой преподавания, зал №2',
        'ФТД: Повышение спортивного мастерства, зал а/г',
        'Научные исследования в сфере физической культуры и спорта (лек)/(пр), К209 (с 17.05)',
        'День самостоятельной работы',
        'Спортивно-педагогические дисциплины (28 ч), зал ф/т (К)',
        'Базы данных (лек), ЭОиДОТ',
        'Базы данных (лек), C',
        'Актерское мастерство (пр),м/зал',
        'Актерское мастерство (пр),м/зал/театр',
        'Актерское мастерство (пр), К625/театр'
    ]

    for input_str in inputs:
        before, campus, aud = extract_campus_audience(input_str, campus_type)
        print("Input:", input_str)
        print("Before:", before)
        print("campus:", campus)
        print("aud:", aud)
        print()