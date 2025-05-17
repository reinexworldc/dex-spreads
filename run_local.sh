#!/bin/bash

# Добавляем режим отладки, чтобы видеть каждую выполняемую команду
set -x

# Скрипт для локального запуска проекта Dex Spreads

echo "Запуск проекта Dex Spreads в локальном режиме"

# Получаем абсолютный путь к директории проекта
PROJECT_DIR=$(pwd)
echo "Директория проекта: $PROJECT_DIR"

# Добавляем отладочную информацию
echo "Текущая директория: $(pwd)"
echo "Содержимое директории:"
ls -la | grep "package.json"
echo "Проверка условия: [ -f \"./package.json\" ] = $( [ -f "./package.json" ] && echo "true" || echo "false" )"
echo "Проверка условия без ./: [ -f \"package.json\" ] = $( [ -f "package.json" ] && echo "true" || echo "false" )"

# Проверка на наличие фронтенда (прямо здесь, в начале скрипта)
echo "Проверка фронтенда перед запуском всего остального..."
if [ -f "package.json" ]; then
    echo "ПЕРЕД ВСЕМ: package.json найден!"
else
    echo "ПЕРЕД ВСЕМ: package.json НЕ найден!"
fi

# Проверяем только наличие npm
has_npm=$(which npm > /dev/null 2>&1 && echo "true" || echo "false")

if [ "$has_npm" = "true" ]; then
    PKG_MANAGER="npm"
    echo "Найден пакетный менеджер: npm"
else
    PKG_MANAGER=""
    echo "ВНИМАНИЕ: Не найден npm. Фронтенд не будет запущен."
fi

# Создаем нужные директории
mkdir -p backend/data

# Устанавливаем переменные окружения
export PYTHONPATH=.

# Запускаем процесс обновления базы данных в фоновом режиме
echo "Запуск обновления базы данных..."
python backend/update_db.py > ./update_db.log 2>&1 &
UPDATE_DB_PID=$!
echo "Процесс обновления БД запущен с PID: $UPDATE_DB_PID"

# Ждем немного, чтобы база данных успела инициализироваться
sleep 2

# Запускаем Flask-сервер в фоновом режиме, используя скобки для сохранения текущей директории
echo "Запуск Flask-сервера..."
(cd backend && python app.py > ../backend.log 2>&1 &)
FLASK_PID=$!
echo "Flask-сервер запущен с PID: $FLASK_PID"

# Проверяем, что мы всё ещё в корневой директории проекта
echo "Текущая директория после запуска Flask: $(pwd)"
if [ "$(pwd)" != "$PROJECT_DIR" ]; then
    echo "Восстанавливаем директорию проекта"
    cd "$PROJECT_DIR"
fi

# Обнуляем PID фронтенда
FRONTEND_PID=""

# Проверка на наличие фронтенда и npm
if [ -f "package.json" ] && [ "$has_npm" = "true" ]; then
    echo "Обнаружен NextJS фронтенд в корневой директории, запускаем с npm..."
    
    # Используем npm с флагом --legacy-peer-deps
    echo "Используем npm для запуска фронтенда"
    npm install --legacy-peer-deps && npm run dev > ./frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Проверяем, что процесс запустился
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Фронтенд успешно запущен с PID: $FRONTEND_PID"
    else
        echo "ВНИМАНИЕ: Не удалось запустить фронтенд"
        FRONTEND_PID=""
    fi
elif [ -d "./frontend" ] && [ "$has_npm" = "true" ]; then
    echo "Обнаружен каталог frontend, запускаем фронтенд..."
    cd frontend

    # Проверяем наличие package.json
    if [ -f "package.json" ]; then
        echo "Используем npm для запуска фронтенда"
        npm install --legacy-peer-deps && npm run dev > ../frontend.log 2>&1 &
        FRONTEND_PID=$!
        
        # Проверяем, что процесс запустился
        if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "Фронтенд успешно запущен с PID: $FRONTEND_PID"
        else
            echo "ВНИМАНИЕ: Не удалось запустить фронтенд"
            FRONTEND_PID=""
        fi
    fi
    cd "$PROJECT_DIR"
else
    if [ -f "package.json" ] && [ "$has_npm" = "false" ]; then
        echo "Фронтенд не запущен: не найден npm"
    else
        echo "Фронтенд не обнаружен, пропускаем запуск фронтенда"
    fi
fi

# Записываем PID процессов в файл для возможности последующей остановки
echo "$UPDATE_DB_PID" > .update_db.pid
echo "$FLASK_PID" > .flask.pid
if [ ! -z "$FRONTEND_PID" ]; then
    echo "$FRONTEND_PID" > .frontend.pid
fi

echo "Все компоненты запущены!"
echo "- Бэкенд доступен по адресу: http://localhost:5000"
if [ ! -z "$FRONTEND_PID" ]; then
    echo "- Фронтенд доступен по адресу: http://localhost:3000"
fi
echo "Логи сохраняются в файлах: update_db.log, backend.log и frontend.log"
echo ""
echo "Для остановки всех процессов выполните: ./stop_local.sh"

# Создаем скрипт для остановки
cat << 'EOF' > stop_local.sh
#!/bin/bash

echo "Останавливаем компоненты проекта Dex Spreads..."

# Останавливаем процессы по сохраненным PID
if [ -f .update_db.pid ]; then
    PID=$(cat .update_db.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем процесс обновления БД (PID: $PID)..."
        kill $PID
    fi
    rm .update_db.pid
fi

if [ -f .flask.pid ]; then
    PID=$(cat .flask.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем Flask-сервер (PID: $PID)..."
        kill $PID
    fi
    rm .flask.pid
fi

if [ -f .frontend.pid ]; then
    PID=$(cat .frontend.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем фронтенд (PID: $PID)..."
        kill $PID
    fi
    rm .frontend.pid
fi

echo "Все процессы остановлены!"
EOF

chmod +x stop_local.sh

# Скрипт для запуска только скрипта обновления БД
cat << 'EOF' > run_updater.sh
#!/bin/bash

echo "Запуск только скрипта обновления базы данных..."

# Создаем нужные директории
mkdir -p backend/data

# Устанавливаем переменные окружения
export PYTHONPATH=.

# Запускаем процесс обновления базы данных
python backend/update_db.py
EOF

chmod +x run_updater.sh 