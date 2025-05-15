@echo off
echo Запуск фронтенда для DEX-Spreads приложения...

REM Проверяем существование папки node_modules
if not exist "node_modules\" (
  echo Папка node_modules не найдена. Устанавливаем зависимости...
  npm install
)

REM Запускаем Next.js в режиме разработки
echo Запускаем Next.js на http://localhost:3000
npm run dev 