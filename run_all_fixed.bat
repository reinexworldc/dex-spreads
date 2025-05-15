@echo off
echo [DEX-Spreads] Запуск фронтенда и бэкенда...

REM Создаем .env.local с правильным URL API
echo Настраиваем переменные окружения...
echo NEXT_PUBLIC_API_URL=http://localhost:5000> .env.local
echo Файл .env.local создан.

REM Устанавливаем зависимости для фронтенда, если нужно
if not exist "node_modules\" (
  echo Устанавливаем зависимости фронтенда...
  call npm install
  echo Зависимости фронтенда установлены.
) else (
  echo Зависимости фронтенда уже установлены.
)

REM Создаем и активируем виртуальное окружение Python для бэкенда
cd backend
if not exist "venv\" (
  echo Создаем виртуальное окружение Python...
  python -m venv venv
  echo Виртуальное окружение создано.
)

REM Активируем виртуальное окружение и устанавливаем зависимости
echo Активируем виртуальное окружение и устанавливаем зависимости...
call venv\Scripts\activate
pip install -r requirements.txt
pip install flask-cors

REM Запускаем бэкенд в отдельном окне
echo Запускаем бэкенд на http://localhost:5000...
start cmd /k "cd %CD% && call venv\Scripts\activate && set FLASK_APP=app.py && set FLASK_DEBUG=1 && python -m flask run --host=0.0.0.0 --port=5000"

REM Возвращаемся в корневую директорию и запускаем фронтенд
cd ..

REM Запускаем фронтенд в отдельном окне
echo Запускаем фронтенд на http://localhost:3000...
start cmd /k "npm run dev"

echo.
echo [DEX-Spreads] Оба сервера запущены:
echo - Фронтенд: http://localhost:3000
echo - API: http://localhost:5000
echo.
echo Для остановки закройте окна командной строки. 