@echo off
echo Запуск main.py для DEX-Spreads на Python 3.13...

cd backend

REM Проверяем существование виртуального окружения
if not exist "venv313\" (
  echo Создаем виртуальное окружение Python 3.13...
  python -m venv venv313
  echo Виртуальное окружение создано.
)

REM Активируем виртуальное окружение и устанавливаем зависимости
echo Активируем виртуальное окружение и устанавливаем зависимости...
call venv313\Scripts\activate
pip install --upgrade pip
echo.
echo Устанавливаем совместимые пакеты для Python 3.13...
pip install -r requirements_py313.txt

echo.
echo Запускаем main.py...
python main.py

pause 