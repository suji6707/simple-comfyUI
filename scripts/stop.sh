#!/bin/bash

# ComfyUI Service - Stop Script

set -e

echo "🛑 Stopping ComfyUI Service..."

# Stop and remove containers
docker-compose down

# Optional: Remove volumes (uncomment to clean database and redis data)
# docker-compose down -v

echo "✅ ComfyUI Service stopped."
echo ""
echo "💡 To completely clean up including volumes and images:"
echo "   docker-compose down -v --rmi all"