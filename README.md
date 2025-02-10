# Веб-приложение для автоматической интеграции расписания СурГУ с сервисом Google Calendar

## Описание проекта

Этот проект позволяет синхронизировать расписание университета с Google Calendar. Основной функционал включает парсинг данных из PDF и Excel файлов, взаимодействие с Google Calendar API, авторизацию через Supabase и работу с базой данных MySQL. Все данные о расписании хранятся PDF формате, преобразовываются и заносяться в базу данных, а затем синхронизируются с Google Calendar для удобства пользователей.

## Стек технологий

- **Frontend**: React
- **Backend**: Django
- **База данных**: MySQL
- **Авторизация**: Supabase (для работы с JWT токенами)
- **API**: Google Calendar API
- **Парсинг данных**: Python, библиотеки для работы с PDF и Excel
- **Развёртывание базы данных**: Бесплатный онлайн хостинг для MySQL

Проект разработал студент СурГУ, группы 609-11: Рузин Данил Евгеньевич 
