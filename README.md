# Yatube

### Описание
Блог-платформа
Социальная сеть

### Технологии
*Python 3.7*
*Django 2.2.19*

### Запуск проекта в dev-режиме
Клонировать репозиторий и перейти в него в командной строке:
```
 git clone https://github.com/Mikhail2690/hw05_final
```
```
 cd yatube
```
Cоздать и активировать виртуальное окружение:
```
 python -m venv venv
```
Для Windows
```
 source venv/Scripts/activate
```
Для Mac
```
 source env/bin/activate
```
Установить зависимости из файла requirements.txt:
```
 python -m pip install --upgrade pip
```
```
 pip install -r requirements.txt
```
Выполнить миграции:
```
 python manage.py migrate
```
Запустить проект:
```
 python manage.py runserver
```
Автор: [Федоренко Михаил](https://github.com/Mikhail2690/)
