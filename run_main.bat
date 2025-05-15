@echo off
echo Запуск main.py для DEX-Spreads...

cd backend

REM Проверяем существование виртуального окружения
if not exist "venv\" (
  echo Создаем виртуальное окружение Python...
  python -m venv venv
  echo Виртуальное окружение создано.
)

REM Активируем виртуальное окружение и устанавливаем зависимости
echo Активируем виртуальное окружение и устанавливаем зависимости...
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo Запускаем main.py...
python main.py

pause 