#!/bin/bash
set -e

echo "🚀 Iniciando aplicación Django con WebSockets en Azure..."
echo "📍 Directorio actual: $(pwd)"
echo "🐍 Python: $(python --version)"

# Verificar si existe manage.py
if [ ! -f "manage.py" ]; then
    echo "❌ ERROR: manage.py no encontrado"
    exit 1
fi

# Colectar archivos estáticos
echo "📦 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Warning: collectstatic falló"

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput || {
    echo "❌ ERROR: Migraciones fallaron"
    exit 1
}

# Verificar migraciones
echo "✅ Verificando tablas de base de datos..."
python manage.py showmigrations

echo "✅ Configuración completada exitosamente"
echo "🌐 Iniciando servidor Daphne en puerto 8000..."

# Iniciar Daphne en el puerto 8000
exec daphne -b 0.0.0.0 -p 8000 proyecto.asgi:application