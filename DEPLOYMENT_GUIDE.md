# Smart Study Hub 2.0 - Deployment Guide

## 🚀 Production Deployment Guide

This guide provides step-by-step instructions untuk deploying Smart Study Hub 2.0 MVP ke production environment.

---

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 20GB SSD
- **CPU**: 2+ cores recommended
- **Network**: Stable internet connection

### Required Software
- **Python**: 3.8+ (Recommended: 3.9+)
- **MongoDB**: 4.4+ (Recommended: 5.0+)
- **Redis**: 6.0+ (Recommended: 6.2+)
- **Nginx**: 1.18+ (untuk reverse proxy)
- **Git**: Latest version

---

## 🛠 Installation Steps

### 1. System Preparation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git nginx curl wget

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list
sudo apt update
sudo apt install -y mongodb-org

# Install Redis
sudo apt install -y redis-server
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install EPEL repository
sudo yum install -y epel-release

# Install required packages
sudo yum install -y python3 python3-pip git nginx curl wget

# Install MongoDB
sudo tee /etc/yum.repos.d/mongodb-org-5.0.repo << EOF
[mongodb-org-5.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/8/mongodb-org/5.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-5.0.asc
EOF

sudo yum install -y mongodb-org redis
```

### 2. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/smart-study-hub
sudo chown $USER:$USER /opt/smart-study-hub
cd /opt/smart-study-hub

# Clone repository
git clone https://github.com/your-username/smart-study-hub-2.0.git .
```

### 3. Python Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 4. Database Configuration

#### MongoDB Setup
```bash
# Start MongoDB service
sudo systemctl start mongod
sudo systemctl enable mongod

# Create database dan user
mongosh << EOF
use smart_study_hub
db.createUser({
  user: "ssh_user",
  pwd: "your_secure_password",
  roles: [
    { role: "readWrite", db: "smart_study_hub" }
  ]
})
EOF
```

#### Redis Setup
```bash
# Configure Redis
sudo nano /etc/redis/redis.conf

# Update these settings:
# maxmemory 256mb
# maxmemory-policy allkeys-lru
# requirepass your_redis_password

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 5. Environment Configuration

```bash
# Create environment file
cp .env.example .env
nano .env
```

#### Environment Variables (.env)
```bash
# Application Settings
APP_NAME="Smart Study Hub 2.0"
APP_VERSION="1.0.0-MVP"
DEBUG=False
SECRET_KEY="your-super-secret-key-here"
API_V1_STR="/api/v1"

# Database Configuration
MONGODB_URL="mongodb://ssh_user:your_secure_password@localhost:27017/smart_study_hub"
DATABASE_NAME="smart_study_hub"

# Redis Configuration
REDIS_URL="redis://:your_redis_password@localhost:6379/0"

# Security Settings
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM="HS256"

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR="/opt/smart-study-hub/uploads"

# Email Configuration (Optional)
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST="smtp.gmail.com"
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"

# Logging
LOG_LEVEL="INFO"
LOG_FILE="/var/log/smart-study-hub/app.log"

# Performance Settings
WORKERS=4
MAX_CONNECTIONS=100
KEEPALIVE=2
```

### 6. Database Initialization

```bash
# Create uploads directory
mkdir -p /opt/smart-study-hub/uploads
mkdir -p /var/log/smart-study-hub

# Set permissions
sudo chown -R $USER:$USER /opt/smart-study-hub
sudo chmod -R 755 /opt/smart-study-hub

# Initialize database dengan sample data
python create_first_admin.py

# Create database indexes
python scripts/create_analytics_indexes.py
```

---

## 🔧 Production Configuration

### 1. Gunicorn Configuration

Create `/opt/smart-study-hub/gunicorn.conf.py`:
```python
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/log/smart-study-hub/access.log"
errorlog = "/var/log/smart-study-hub/error.log"
loglevel = "info"

# Process naming
proc_name = "smart-study-hub"

# Server mechanics
daemon = False
pidfile = "/var/run/smart-study-hub.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (if using HTTPS directly)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

### 2. Systemd Service

Create `/etc/systemd/system/smart-study-hub.service`:
```ini
[Unit]
Description=Smart Study Hub 2.0 FastAPI Application
After=network.target mongodb.service redis.service
Requires=mongodb.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/smart-study-hub
Environment=PATH=/opt/smart-study-hub/venv/bin
ExecStart=/opt/smart-study-hub/venv/bin/gunicorn -c gunicorn.conf.py app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/smart-study-hub`:
```nginx
upstream smart_study_hub {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # File Upload Size
    client_max_body_size 10M;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static Files
    location /static/ {
        alias /opt/smart-study-hub/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # File Uploads
    location /uploads/ {
        alias /opt/smart-study-hub/uploads/;
        expires 1d;
        add_header Cache-Control "private";
    }

    # API Routes
    location / {
        proxy_pass http://smart_study_hub;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        
        # WebSocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health Check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## 🚀 Deployment Process

### 1. Enable Services

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable smart-study-hub
sudo systemctl start smart-study-hub

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/smart-study-hub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Check service status
sudo systemctl status smart-study-hub
sudo systemctl status nginx
```

### 2. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Or iptables
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

---

## 📊 Monitoring & Maintenance

### 1. Log Monitoring

```bash
# Application logs
sudo tail -f /var/log/smart-study-hub/app.log
sudo tail -f /var/log/smart-study-hub/access.log
sudo tail -f /var/log/smart-study-hub/error.log

# System logs
sudo journalctl -u smart-study-hub -f
sudo journalctl -u nginx -f
```

### 2. Performance Monitoring

```bash
# System resources
htop
iostat -x 1
free -h
df -h

# Application metrics
curl http://localhost:8000/api/v1/system/health
curl http://localhost:8000/api/v1/system/metrics
```

### 3. Database Maintenance

```bash
# MongoDB maintenance
mongosh smart_study_hub --eval "db.runCommand({compact: 'collection_name'})"
mongosh smart_study_hub --eval "db.stats()"

# Redis maintenance
redis-cli INFO memory
redis-cli FLUSHDB  # Only if needed
```

### 4. Backup Strategy

```bash
# Create backup script
sudo nano /opt/smart-study-hub/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backup/smart-study-hub"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# MongoDB backup
mongodump --host localhost --port 27017 --db smart_study_hub --out $BACKUP_DIR/mongodb_$DATE

# Files backup
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/smart-study-hub/uploads

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable dan schedule
sudo chmod +x /opt/smart-study-hub/scripts/backup.sh
sudo crontab -e
# Add: 0 2 * * * /opt/smart-study-hub/scripts/backup.sh
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
sudo journalctl -u smart-study-hub --no-pager -l

# Check configuration
sudo -u www-data /opt/smart-study-hub/venv/bin/python -m app.main

# Check permissions
sudo chown -R www-data:www-data /opt/smart-study-hub
```

#### 2. Database Connection Issues
```bash
# Test MongoDB connection
mongosh "mongodb://ssh_user:password@localhost:27017/smart_study_hub"

# Test Redis connection
redis-cli -a your_redis_password ping
```

#### 3. High Memory Usage
```bash
# Check processes
ps aux --sort=-%mem | head

# Restart services
sudo systemctl restart smart-study-hub
sudo systemctl restart redis-server
```

#### 4. Slow Performance
```bash
# Check database indexes
mongosh smart_study_hub --eval "db.collection.getIndexes()"

# Monitor queries
mongosh smart_study_hub --eval "db.setProfilingLevel(2)"

# Check Redis memory
redis-cli INFO memory
```

---

## 🔄 Updates & Maintenance

### Application Updates

```bash
# Backup current version
cp -r /opt/smart-study-hub /opt/smart-study-hub.backup

# Pull latest changes
cd /opt/smart-study-hub
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations (if any)
python scripts/migrate.py

# Restart service
sudo systemctl restart smart-study-hub
```

### Security Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Check for security advisories
sudo apt list --upgradable

# Update SSL certificates
sudo certbot renew
```

---

## 📞 Support & Resources

### Health Checks
- Application: `https://your-domain.com/api/v1/system/health`
- Database: `https://your-domain.com/api/v1/system/db-status`
- Cache: `https://your-domain.com/api/v1/system/cache-status`

### Documentation
- API Docs: `https://your-domain.com/docs`
- Admin Guide: `https://your-domain.com/admin-guide`

### Emergency Contacts
- System Administrator: admin@your-domain.com
- Development Team: dev@your-domain.com
- 24/7 Support: +1-xxx-xxx-xxxx

---

**🎯 Production Ready!**

Following this guide akan menghasilkan production-ready deployment dari Smart Study Hub 2.0 MVP dengan optimal performance, security, dan reliability.
