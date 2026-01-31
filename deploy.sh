#!/bin/bash

# Deployment script for Siblore POS with load balancing

set -e

echo "Starting deployment of Siblore POS with load balancing..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo " Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your production settings before running again."
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "Building Docker images..."
docker-compose build

echo "Running database migrations..."
docker-compose run --rm web python manage.py migrate --settings=core.settings_prod

echo "Collecting static files..."
docker-compose run --rm web python manage.py collectstatic --noinput --settings=core.settings_prod

echo "Creating superuser (optional)..."
read -p "Do you want to create a superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose run --rm web python manage.py createsuperuser --settings=core.settings_prod
fi

echo "Starting services..."
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 30

echo "Checking service health..."
docker-compose ps

echo "Deployment complete!"
echo ""
echo "Your application is available at: http://localhost"
echo "Flower monitoring at: http://localhost:5555"
echo "View logs with: docker-compose logs -f"
echo ""
echo "Useful commands:"
echo "  - Stop services: docker-compose down"
echo "  - View logs: docker-compose logs -f [service_name]"
echo "  - Restart services: docker-compose restart"
echo "  - Scale web servers: docker-compose up -d --scale web=3"
