#!/bin/sh
set -e

echo "Esperando base de datos..."
until python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')" 2>/dev/null; do
  sleep 1
done
echo "Base de datos lista"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
