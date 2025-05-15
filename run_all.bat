@echo off
echo Запуск DEX-Spreads приложения (фронтенд и бэкенд)...

REM Создаем и запускаем бэкенд в отдельном окне
start cmd /k "cd backend && (if not exist venv\ (echo Создаем виртуальное окружение и устанавливаем зависимости... && python -m venv venv && call venv\Scripts\activate && pip install -r requirements.txt) else (echo Активируем виртуальное окружение... && call venv\Scripts\activate && pip install -r requirements.txt)) && echo Запускаем main.py... && python main.py"

REM Запускаем фронтенд в отдельном окне
start cmd /k "echo Запуск фронтенда... && (if not exist node_modules\ (echo Устанавливаем зависимости... && npm install)) && echo Запускаем Next.js на http://localhost:3000 && npm run dev"

echo Оба сервера запущены. Приложение будет доступно по адресу: http://localhost:3000
echo Бэкенд API доступен по адресу: http://localhost:5000
echo.
echo Для остановки закройте оба окна командной строки. 