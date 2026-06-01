#!/bin/bash
# deploy.sh — actualiza MiPolla en el servidor
set -e

cd /opt/mipolla
echo "→ Pulling latest code..."
git pull origin main

echo "→ Rebuilding and restarting..."
docker compose -f docker-compose.prod.yml up -d --build

echo "→ Running migrations..."
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

echo "→ Collecting static files..."
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

echo "✓ Deploy complete"
docker compose -f docker-compose.prod.yml ps
