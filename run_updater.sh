#!/bin/bash

echo "Запуск только скрипта обновления базы данных..."

# Создаем нужные директории
mkdir -p backend/data

# Устанавливаем переменные окружения
export PYTHONPATH=.

# Запускаем процесс обновления базы данных
python backend/update_db.py
