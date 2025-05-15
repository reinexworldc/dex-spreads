FROM nginx:stable-alpine

# Удаляем стандартную конфигурацию
RUN rm /etc/nginx/conf.d/default.conf

# Копируем нашу конфигурацию
COPY nginx.conf /etc/nginx/nginx.conf

# Экспонируем порт 80
EXPOSE 80

# Команда для запуска Nginx в режиме, который остается активным в фоне
CMD ["nginx", "-g", "daemon off;"] 