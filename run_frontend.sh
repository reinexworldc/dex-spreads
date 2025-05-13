#!/bin/bash

# Устанавливаем зависимости, если они еще не установлены
if [ ! -d "node_modules" ]; then
  echo "Устанавливаем зависимости..."
  npm install
fi

# Запускаем Next.js в режиме разработки
echo "Запускаем Next.js на http://localhost:3000"
npm run dev 