import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from main.models import Campus, Time, TimeGroup


def extract_time_campus(url: str) -> dict:
    """
    Извлекает данные о расписании звонков в разных корпусах.

    :param url: URL-адрес страницы с данными о расписании.
    :return: Словарь с данными о расписании.
    """
    time_data = {}
    campus_time_group = {
        1: ['А', 'Г', 'К', 'У'],
        2: ['МК'],
        3: ['С'],
        4: ['Водолей'],
    }

    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        post_text_div = soup.find_all("div", class_="post_text")
        tables = post_text_div[1].find_all("table")

        for index, table in enumerate(tables, start=1):
            rows = table.find_all("tr")

            time_data.setdefault(index, {})
            time_data[index]['campus'] = campus_time_group[index]

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                pair_number = int(re.sub(r'\D', '', cells[0].get_text()))
                start_time, end_time = cells[1].get_text().split('-')
                timeout_value = re.sub(r'\D', '', cells[2].get_text())
                timeout = f"00:{timeout_value if timeout_value else '00'}"

                pair_data = {
                    "start_time": start_time.strip(),
                    "end_time": end_time.strip(),
                    "timeout": timeout.strip(),
                }
                time_data[index][pair_number] = pair_data

    except Exception as e:
        print(f"Ошибка при парсинге: {e}")

    return time_data


class Command(BaseCommand):
    help = "Парсинг расписания звонков и добавление данных в БД"

    def handle(self, *args, **kwargs):
        url = "http://www.surgu.ru/ucheba/raspisanie-zvonkov"
        parsed_data = extract_time_campus(url)
        print(parsed_data)
        for group_number, group_data in parsed_data.items():
            # Создание или получение TimeGroup
            time_group, _ = TimeGroup.objects.get_or_create(number_time_group=group_number)

            # Обновление или создание корпусов
            for campus_short_name in group_data["campus"]:
                campus = Campus.objects.filter(reduction=campus_short_name).first()
                if campus:
                    campus.time_group = time_group
                    campus.save()

            # Обновление или создание времени занятий
            for pair_number, pair_data in group_data.items():
                if pair_number == "campus":  # Пропуск ключа "campus"
                    continue

                Time.objects.update_or_create(
                    time_group=time_group,
                    number_lesson=pair_number,
                    defaults={
                        "time_start": pair_data["start_time"],
                        "time_end": pair_data["end_time"],
                        "time_out": pair_data["timeout"],
                    },
                )

        print('Данные о звонках успешно добавлены в БД.')
