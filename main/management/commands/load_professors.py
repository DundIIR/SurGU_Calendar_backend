import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from main.models import Professor, Department


def extract_professor_FIO(url: str) -> dict:
    """
    Парсит таблицу с преподавателями и возвращает их данные в виде словаря.
    """
    professor = {}
    start_link = 'http://www.surgu.ru'

    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        html_content = response.content

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="table table-bordered table-sm")
        if not table:
            raise ValueError("Таблица не найдена на странице")

        rows = table.find_all("tr", itemprop="teachingOp")
        for row in rows:
            edu_name_cell = row.find("td", itemprop="eduName")
            if not edu_name_cell:
                continue
            link = edu_name_cell.find("a")
            if not link or not link.get("href"):
                continue
            i = 1
            print('Ссылка обрабатывается', i)
            i += 1
            next_page_url = start_link + link["href"]
            try:
                next_page_response = requests.get(next_page_url, verify=False)
                next_page_response.raise_for_status()
                next_page_content = next_page_response.content

                next_page_soup = BeautifulSoup(next_page_content, "html.parser")
                teaching_rows = next_page_soup.find_all("tr", itemprop="teachingStaff")

                for teaching_row in teaching_rows:
                    fio_cell = teaching_row.find("td", itemprop="fio")
                    post_cell = teaching_row.find("td", itemprop="post")

                    if fio_cell and post_cell:
                        fio = fio_cell.get_text().strip()
                        post = post_cell.get_text().strip()
                        fio_parts = fio.split()
                        if len(fio_parts) == 3:
                            last_name, first_name, patronymic = fio_parts
                            key = f"{last_name} {first_name[0]}.{patronymic[0]}."

                            if key not in professor:
                                professor[key] = {
                                    "last_name": last_name,
                                    "first_name": first_name,
                                    "patronymic": patronymic,
                                    "post": post,
                                }


            except Exception as e:
                print(f"Ошибка при переходе по ссылке {next_page_url}: {e}")

        professor['вакансия'] = 'None'

    except Exception as e:
        print(f"Произошла ошибка: {e}")

    return professor


class Command(BaseCommand):
    help = "Загружает данные преподавателей в базу данных"

    def handle(self, *args, **options):
        url = "http://www.surgu.ru/sveden/employees"
        result = extract_professor_FIO(url)

        department = Department.objects.get(pk=1)
        for key, data in result.items():
            print(key)
            if key == "вакансия":
                continue

            # Добавляем преподавателя в БД, если его ещё нет
            Professor.objects.update_or_create(
                last_name=data["last_name"],
                first_name=data["first_name"],
                patronymic=data["patronymic"],
                defaults={
                    "post": data["post"],
                    "department": department,
                },
            )
        print('Данные преподавателей успешно добавлены в базу данных.')
