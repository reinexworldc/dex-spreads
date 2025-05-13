#!/bin/bash

# Вывести информацию о запуске
echo "====================== DEX Spread Monitor ======================"
echo "Запускаем приложение DEX Spread Monitor"
echo "Для работы приложения необходимо запустить бэкенд и фронтенд"
echo "=============================================================="
echo ""

# Запускаем бэкенд в отдельном терминале
echo "Запускаем бэкенд (Flask)..."
gnome-terminal --title="DEX Spread Monitor - Backend" -- bash -c "./run_backend.sh; exec bash" || \
xterm -T "DEX Spread Monitor - Backend" -e "./run_backend.sh; exec bash" || \
konsole --new-tab -p tabtitle="DEX Spread Monitor - Backend" -e "./run_backend.sh; exec bash" || \
mate-terminal --title="DEX Spread Monitor - Backend" -e "./run_backend.sh; exec bash" || \
./run_backend.sh &

# Немного ждем, чтобы бэкенд успел запуститься
sleep 3

# Запускаем фронтенд в текущем терминале
echo "Запускаем фронтенд (Next.js)..."
./run_frontend.sh 