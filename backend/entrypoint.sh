#!/bin/bash
# Entrypoint script para esperar a que PostgreSQL esté listo

set -e

echo "Esperando a que PostgreSQL esté listo..."

# Esperar hasta que PostgreSQL acepte conexiones
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  >&2 echo "PostgreSQL no está disponible aún - esperando..."
  sleep 2
done

>&2 echo "PostgreSQL está listo - ejecutando migraciones..."

# Ejecutar migraciones
python manage.py migrate

echo "Migraciones completadas. Iniciando servidor..."

# Ejecutar el comando principal
exec "$@"
