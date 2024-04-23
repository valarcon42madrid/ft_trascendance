#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python manage.py migrate

# Verificar si el superusuario "admin" ya existe
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', '', '$ADMINPASS')"

# Verificar si el usuario "staff" ya existe
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='staff').exists() or User.objects.create_user('staff', '', '$STAFFPASS', is_staff=True)"

exec "$@"
