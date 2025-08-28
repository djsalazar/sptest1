#!/bin/bash
# Script para refrescar contenedores con la última versión del repo

echo "🚧 Bajando contenedores y borrando volúmenes..."
docker compose down -v

echo "⬇️ Haciendo pull del repo..."
git pull origin main

echo "🔨 Rebuild de imágenes sin cache..."
docker compose build --no-cache

echo "🚀 Levantando contenedores en segundo plano..."
docker compose up -d

echo "✅ Proceso completo"
