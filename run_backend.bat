@echo off
echo Запуск бэкенда DEX-Spreads...

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

REM Устанавливаем переменные окружения Flask
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1

echo.
echo Запускаем Flask-сервер на http://localhost:5000
flask run --host=0.0.0.0 --port=5000

REM Если требуется запуск main.py напрямую:
REM echo Запускаем main.py
REM python main.py 