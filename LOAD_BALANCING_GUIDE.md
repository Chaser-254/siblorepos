# Load Balancing Setup Guide for Siblore POS

## Overview
This guide explains how to deploy your Django POS system with load balancing to handle multiple concurrent users efficiently.

## Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Nginx     │────│   Django    │────│ PostgreSQL  │
│ Load Balancer│    │  (Multiple  │    │  Database   │
│             │    │  Workers)   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Redis     │    │   Celery    │    │   Flower    │
│   Cache     │    │  Workers    │    │ Monitoring  │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Performance Improvements

### 1. Database Optimization
- **PostgreSQL**: Replaced SQLite with PostgreSQL for better concurrent performance
- **Connection Pooling**: Configured database connection pooling (20 connections max)
- **Persistent Connections**: Enabled `CONN_MAX_AGE = 60` for connection reuse

### 2. Caching Layer
- **Redis**: Added Redis caching for frequently accessed data
- **Session Storage**: Moved sessions from file-based to Redis cache
- **Query Optimization**: Enabled `USE_SELECT_RELATED` and `USE_PREFETCH_RELATED`

### 3. Web Server Optimization
- **Gunicorn**: Production WSGI server with multiple workers
- **Nginx**: Reverse proxy with load balancing and static file serving
- **Compression**: Gzip compression enabled for faster content delivery

### 4. Background Tasks
- **Celery**: Asynchronous task processing for heavy operations
- **Flower**: Monitoring dashboard for Celery tasks

## Deployment Steps

### Prerequisites
- Docker and Docker Compose installed
- PostgreSQL and Redis servers (or use Docker images)
- At least 4GB RAM for optimal performance

### Quick Start
```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Edit .env with your settings
nano .env

# 3. Deploy with the script
chmod +x deploy.sh
./deploy.sh
```

### Manual Deployment
```bash
# Build and start services
docker-compose up -d

# Run migrations
docker-compose run --rm web python manage.py migrate --settings=core.settings_prod

# Collect static files
docker-compose run --rm web python manage.py collectstatic --noinput --settings=core.settings_prod

# Create superuser
docker-compose run --rm web python manage.py createsuperuser --settings=core.settings_prod
```

## Scaling Options

### Horizontal Scaling
```bash
# Scale web servers to handle more traffic
docker-compose up -d --scale web=3

# Scale Celery workers for background tasks
docker-compose up -d --scale celery=2
```

### Performance Tuning

#### Database Optimization
```sql
-- Add indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_products_category ON products_product(category_id);
CREATE INDEX CONCURRENTLY idx_sales_customer ON sales_sale(customer_id);
CREATE INDEX CONCURRENTLY idx_sales_date ON sales_sale(created_at);
```

#### Redis Configuration
```bash
# Increase Redis memory limit
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### Nginx Tuning
```nginx
# Add to nginx.conf for better performance
worker_processes auto;
worker_connections 2048;

# Enable HTTP/2
listen 443 ssl http2;
```

## Monitoring

### Application Monitoring
- **Flower**: http://localhost:5555 (Celery task monitoring)
- **Logs**: `docker-compose logs -f`
- **Health Check**: http://localhost/health/

### Performance Metrics
Monitor these key metrics:
- Response time: < 200ms for most requests
- Database connections: < 80% of pool size
- Redis memory usage: < 80% of allocated memory
- CPU usage: < 70% on average

## Load Testing

### Using Apache Bench
```bash
# Test login endpoint
ab -n 1000 -c 50 http://localhost/login/

# Test product listing
ab -n 1000 -c 100 http://localhost/products/
```

### Using Locust
Create a `locustfile.py`:
```python
from locust import HttpUser, task, between

class POSUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.client.get("/login/")
    
    @task(3)
    def view_products(self):
        self.client.get("/products/")
    
    @task(2)
    def view_sales(self):
        self.client.get("/sales/dashboard/")
```

Run Locust:
```bash
locust -f locustfile.py --host=http://localhost
```

## Security Considerations

### Rate Limiting
- Login endpoints: 5 requests per minute
- API endpoints: 20 requests per second
- Configured in Nginx with `limit_req_zone`

### SSL/TLS
- Enable HTTPS in production
- Configure SSL certificates in Nginx
- Update `ALLOWED_HOSTS` and security settings

### Database Security
- Use strong passwords
- Enable SSL connections
- Regular backups

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database status
docker-compose logs db

# Increase connection pool size
# Edit DATABASE_POOL_SIZE in .env
```

#### Redis Connection Issues
```bash
# Check Redis status
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### High Memory Usage
```bash
# Monitor resource usage
docker stats

# Restart services if needed
docker-compose restart
```

### Performance Tips

1. **Database Queries**: Use `select_related` and `prefetch_related` in views
2. **Caching**: Cache frequently accessed data with Redis
3. **Static Files**: Serve via CDN in production
4. **Images**: Optimize and compress product images
5. **Background Tasks**: Move heavy operations to Celery

## Expected Performance

With this setup, you should be able to handle:
- **Concurrent Users**: 100-500 simultaneous users
- **Requests/Second**: 1000+ RPS
- **Response Time**: < 200ms average
- **Database Load**: Distributed across connection pool

## Maintenance

### Regular Tasks
```bash
# Update dependencies
docker-compose build --no-cache

# Database backups
docker-compose exec db pg_dump siblore_pos > backup.sql

# Log rotation
docker-compose exec web find logs/ -name "*.log" -mtime +7 -delete
```

### Monitoring Setup
Consider setting up:
- Prometheus + Grafana for metrics
- Sentry for error tracking
- ELK stack for log analysis

## Support

For issues:
1. Check logs: `docker-compose logs -f [service]`
2. Verify configuration in `.env`
3. Ensure all services are running: `docker-compose ps`
4. Monitor resource usage: `docker stats`
