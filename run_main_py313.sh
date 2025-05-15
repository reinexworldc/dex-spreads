#!/bin/bash

echo "Запуск main.py для DEX-Spreads на Python 3.13..."

# Переходим в директорию бэкенда
cd backend

# Проверяем существование виртуального окружения
if [ ! -d "venv313" ]; then
  echo "Создаем виртуальное окружение Python 3.13..."
  python3 -m venv venv313
  echo "Виртуальное окружение создано."
fi

# Активируем виртуальное окружение и устанавливаем зависимости
echo "Активируем виртуальное окружение и устанавливаем зависимости..."
source venv313/bin/activate
pip install --upgrade pip
echo
echo "Устанавливаем совместимые пакеты для Python 3.13..."
pip install -r requirements_py313.txt

echo
echo "Запускаем main.py..."
python main.py

# Деактивируем виртуальное окружение при выходе
deactivate 