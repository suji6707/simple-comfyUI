#!/bin/bash

# ComfyUI Service - Development Startup Script

set -e

echo "🚀 Starting ComfyUI Service Development Environment"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please update the values as needed."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/models backend/uploads frontend/public/generated

# Build and start services
echo "🔨 Building and starting services..."
docker compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL
# echo "  - Waiting for PostgreSQL..."
# until docker compose exec postgres pg_isready -U user; do
#     sleep 1
# done

# Wait for Redis
# echo "  - Waiting for Redis..."
# until docker compose exec redis redis-cli ping; do
#     sleep 1
# done

# Wait for backend
echo "  - Waiting for backend API..."
until curl -s http://localhost:8000/health > /dev/null; do
    sleep 2
done

# Wait for frontend
echo "  - Waiting for frontend..."
until curl -s http://localhost:3000 > /dev/null; do
    sleep 2
done

echo ""
echo "✅ ComfyUI Service is ready!"
echo ""
echo "🌐 Frontend:     http://localhost:3000"
echo "🔧 Backend API:  http://localhost:8000"
echo "📖 API Docs:     http://localhost:8000/api/v1/docs"
echo "🌸 Flower UI:    http://localhost:5555"
echo "📊 MinIO:        http://localhost:9001"
echo ""
echo "📋 Useful commands:"
echo "  docker compose logs -f          # View logs"
echo "  docker compose logs -f backend  # View backend logs only"
echo "  docker compose ps               # View running services"
echo "  docker compose down             # Stop all services"
echo "  ./scripts/stop.sh               # Stop and cleanup"
echo ""