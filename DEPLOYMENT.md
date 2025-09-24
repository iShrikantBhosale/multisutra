# Deployment Guide for MultiSutra CMS

This guide covers various deployment options for MultiSutra CMS, from development to production environments.

## Prerequisites

- Python 3.11+
- PostgreSQL (for production)
- Redis (for caching and rate limiting)
- Domain name with wildcard subdomain support

## Development Setup

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <your-repo>
   cd multisutra
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

3. **Initialize database**:
   ```bash
   export FLASK_APP=app.py
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

4. **Create super admin**:
   ```bash
   python app.py create-super-admin
   ```

5. **Run development server**:
   ```bash
   python app.py
   ```

### Docker Development

```bash
docker-compose up --build
docker-compose exec web flask db upgrade
docker-compose exec web python app.py create-super-admin
```

## Production Deployment

### Option 1: Deploy to Render (Recommended)

Render provides easy deployment with managed PostgreSQL and Redis.

#### Step 1: Prepare Repository

1. Fork/clone the repository to your GitHub account
2. Ensure all files are committed and pushed

#### Step 2: Create Render Services

1. **Create Web Service**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - Name: `multisutra-cms`
     - Environment: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 4 app:app`

2. **Create PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - Name: `multisutra-db`
   - Plan: Choose appropriate plan

3. **Create Redis Instance**:
   - Click "New +" → "Redis"
   - Name: `multisutra-redis`
   - Plan: Choose appropriate plan

#### Step 3: Configure Environment Variables

In your web service settings, add these environment variables:

```bash
# Required
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=[Auto-filled from database]
REDIS_URL=[Auto-filled from Redis]

# Domain Configuration
MAIN_DOMAIN=yourdomain.com
ALLOWED_SUBDOMAINS=blog1,blog2,demo

# Email (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# External Services (optional)
GOOGLE_ANALYTICS_ID=UA-XXXXXXXXX-X
SENTRY_DSN=your-sentry-dsn

# File Uploads
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216

# Security
BCRYPT_LOG_ROUNDS=12
```

#### Step 4: Custom Domain Setup

1. **In Render Dashboard**:
   - Go to your web service settings
   - Click "Custom Domains"
   - Add your domain: `yourdomain.com`
   - Add wildcard domain: `*.yourdomain.com`

2. **DNS Configuration**:
   ```
   Type: A
   Name: @
   Value: [Render IP address]
   
   Type: CNAME
   Name: *
   Value: yourdomain.com
   ```

#### Step 5: Initialize Database

1. Go to your web service in Render
2. Open the "Shell" tab
3. Run initialization commands:
   ```bash
   flask db upgrade
   python app.py create-super-admin
   python app.py seed-data  # Optional: create sample data
   ```

### Option 2: Docker Production Deployment

#### Step 1: Prepare Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/multisutra_cms
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - MAIN_DOMAIN=${MAIN_DOMAIN}
    depends_on:
      - db
      - redis
    volumes:
      - ./static/uploads:/app/static/uploads
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=multisutra_cms
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./static:/var/www/static
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Step 2: Create Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server web:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com *.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com *.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /static {
            alias /var/www/static;
            expires 30d;
            add_header Cache-Control "public, no-transform";
        }
    }
}
```

#### Step 3: Environment Variables

Create `.env.prod`:

```bash
SECRET_KEY=your-production-secret-key
POSTGRES_PASSWORD=secure-database-password
MAIN_DOMAIN=yourdomain.com
FLASK_ENV=production
```

#### Step 4: Deploy

```bash
# Set up SSL certificate first
certbot certonly --standalone -d yourdomain.com -d *.yourdomain.com

# Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Initialize database
docker-compose -f docker-compose.prod.yml exec web flask db upgrade
docker-compose -f docker-compose.prod.yml exec web python app.py create-super-admin
```

### Option 3: Manual VPS Deployment

#### Step 1: Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib redis-server

# Create user
sudo adduser multisutra
sudo usermod -aG sudo multisutra
```

#### Step 2: Database Setup

```bash
sudo -u postgres createuser --interactive
# Create user: multisutra
# Superuser: y

sudo -u postgres createdb multisutra_cms -O multisutra
```

#### Step 3: Application Setup

```bash
# Switch to app user
sudo su - multisutra

# Clone repository
git clone <your-repo> multisutra-cms
cd multisutra-cms

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Configure environment
cp .env.example .env
# Edit .env with production settings

# Initialize database
export FLASK_APP=app.py
flask db upgrade
python app.py create-super-admin
```

#### Step 4: Systemd Service

Create `/etc/systemd/system/multisutra.service`:

```ini
[Unit]
Description=MultiSutra CMS
After=network.target

[Service]
User=multisutra
WorkingDirectory=/home/multisutra/multisutra-cms
Environment=PATH=/home/multisutra/multisutra-cms/venv/bin
EnvironmentFile=/home/multisutra/multisutra-cms/.env
ExecStart=/home/multisutra/multisutra-cms/venv/bin/gunicorn --bind unix:/tmp/multisutra.sock --workers 4 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable multisutra
sudo systemctl start multisutra
```

#### Step 5: Nginx Configuration

Create `/etc/nginx/sites-available/multisutra`:

```nginx
server {
    listen 80;
    server_name yourdomain.com *.yourdomain.com;

    location / {
        proxy_pass http://unix:/tmp/multisutra.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/multisutra/multisutra-cms/static;
        expires 30d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/multisutra /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL Certificate Setup

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d *.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Maintenance

### Health Checks

Create `/health` endpoint in your Flask app:

```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow()}
```

### Logging

Configure logging in production:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/multisutra.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

### Backups

#### Database Backup Script

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/home/multisutra/backups"
DB_NAME="multisutra_cms"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /home/multisutra/backup.sh
```

### Performance Optimization

1. **Enable Redis caching**:
   ```python
   CACHE_TYPE = 'redis'
   CACHE_REDIS_URL = 'redis://localhost:6379/0'
   ```

2. **Configure Gunicorn**:
   ```bash
   gunicorn --workers 4 --worker-class gevent --worker-connections 1000 --bind 0.0.0.0:8000 app:app
   ```

3. **Database optimization**:
   ```sql
   CREATE INDEX CONCURRENTLY idx_posts_tenant_status ON posts(tenant_id, status);
   CREATE INDEX CONCURRENTLY idx_posts_published_at ON posts(published_at DESC) WHERE status = 'published';
   ```

## Troubleshooting

### Common Issues

1. **Subdomain not resolving**:
   - Check DNS wildcard configuration
   - Verify Nginx server_name includes `*.yourdomain.com`

2. **Database connection errors**:
   - Check DATABASE_URL format
   - Verify PostgreSQL is running
   - Check user permissions

3. **File upload issues**:
   - Check directory permissions: `chmod 755 static/uploads`
   - Verify MAX_CONTENT_LENGTH setting

4. **SSL certificate issues**:
   - Ensure DNS is properly configured before running certbot
   - Check certificate paths in Nginx config

### Performance Issues

1. **Slow database queries**:
   - Add database indexes
   - Enable query logging
   - Use connection pooling

2. **High memory usage**:
   - Reduce Gunicorn workers
   - Enable Redis caching
   - Optimize image sizes

3. **Slow static file loading**:
   - Use CDN for static files
   - Enable Nginx gzip compression
   - Set proper cache headers

## Security Considerations

1. **Keep dependencies updated**:
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **Regular security audits**:
   ```bash
   pip install safety
   safety check
   ```

3. **Firewall configuration**:
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   ```

4. **Database security**:
   - Use strong passwords
   - Limit database user permissions
   - Enable SSL for database connections

This deployment guide should help you get MultiSutra CMS running in production. Choose the deployment method that best fits your needs and infrastructure.