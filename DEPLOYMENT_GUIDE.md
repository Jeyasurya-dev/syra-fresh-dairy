# SYRA Fresh Production Deployment Guide

## 🎯 Pre-Deployment Checklist

### Infrastructure Setup

- [ ] Linux server (Ubuntu 20.04 LTS recommended)
- [ ] MongoDB 4.0+ installed and running
- [ ] Python 3.8+ installed
- [ ] Nginx configured as reverse proxy
- [ ] SSL/TLS certificate (Let's Encrypt)
- [ ] Domain name configured

### Services & Credentials

- [ ] SendGrid account (Email notifications)
- [ ] Twilio account (SMS notifications)
- [ ] Meta WhatsApp Cloud API access
- [ ] Razorpay merchant account
- [ ] Google Maps API key (optional)

---

## 📦 Backend Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv mongodb nginx git

# Create app user
sudo useradd -m -s /bin/bash syra
sudo su - syra
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository> syra-fresh
cd syra-fresh/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with production credentials
```

### 3. Environment Configuration (.env)

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here-change-this

# Database
MONGO_URI=mongodb://localhost:27017/syra_fresh_prod
DB_NAME=syra_fresh_prod

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24 hours

# CORS
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# File Upload
UPLOAD_FOLDER=/var/www/syra-fresh/uploads
MAX_UPLOAD_SIZE=52428800  # 50MB

# Email (SendGrid)
SENDGRID_API_KEY=your-sendgrid-key
FROM_EMAIL=noreply@yourdomain.com

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# SMS Alternative (Fast2SMS)
FAST2SMS_API_KEY=your-fast2sms-key

# WhatsApp (Meta)
WHATSAPP_BUSINESS_ACCOUNT_ID=your-account-id
WHATSAPP_BUSINESS_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_ACCESS_TOKEN=your-access-token

# Razorpay
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret

# Admin Email
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=change-this-in-panel

# Google Maps (Optional)
GOOGLE_MAPS_API_KEY=your-api-key

# Monitoring
LOG_LEVEL=INFO
LOG_FILE=/var/log/syra-fresh/app.log
```

### 4. Database Setup

```bash
# Start MongoDB
sudo systemctl start mongodb
sudo systemctl enable mongodb

# Create database user (if using authentication)
mongosh
> use syra_fresh_prod
> db.createUser({
  user: "syra_user",
  pwd: "strong-password-here",
  roles: ["readWrite"]
})
```

### 5. Seed Initial Data

```bash
cd /home/syra/syra-fresh/backend
source venv/bin/activate
python seed.py
```

### 6. Systemd Service File

Create `/etc/systemd/system/syra-backend.service`:

```ini
[Unit]
Description=SYRA Fresh Backend
After=network.target mongodb.service
Wants=mongodb.service

[Service]
Type=notify
User=syra
WorkingDirectory=/home/syra/syra-fresh/backend
ExecStart=/home/syra/syra-fresh/backend/venv/bin/gunicorn \
  --workers 4 \
  --worker-class sync \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile /var/log/syra-fresh/access.log \
  --error-logfile /var/log/syra-fresh/error.log \
  --log-level info \
  app:app

Restart=always
RestartSec=10

# Environment variables
EnvironmentFile=/home/syra/syra-fresh/backend/.env

[Install]
WantedBy=multi-user.target
```

### 7. Start Backend Service

```bash
sudo systemctl daemon-reload
sudo systemctl start syra-backend
sudo systemctl enable syra-backend
sudo systemctl status syra-backend

# View logs
sudo journalctl -u syra-backend -f
```

---

## 🌐 Frontend Deployment

### 1. Setup Frontend Directory

```bash
sudo mkdir -p /var/www/syra-fresh/frontend
sudo chown -R www-data:www-data /var/www/syra-fresh/
sudo chmod -R 755 /var/www/syra-fresh/

# Copy frontend files
sudo cp -r /home/syra/syra-fresh/frontend/* /var/www/syra-fresh/frontend/
```

### 2. Configure API Endpoints

Edit `/var/www/syra-fresh/frontend/js/api.js`:

```javascript
const API_URL = "https://api.yourdomain.com";  // Production API URL
const DELIVERY_API_URL = "https://api.yourdomain.com/api/delivery";
const ADMIN_API_URL = "https://api.yourdomain.com/api/admin";
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/syra-fresh`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Root directory
    root /var/www/syra-fresh/frontend;
    index index.html;

    # Frontend routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static files caching
    location ~* \.(css|js|gif|jpe?g|png|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS Headers
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        
        # Handle OPTIONS requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }

    # Security - Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Logging
    access_log /var/log/nginx/syra-fresh-access.log;
    error_log /var/log/nginx/syra-fresh-error.log;

    # File upload limit
    client_max_body_size 50M;
}
```

### 4. Enable Nginx Site

```bash
sudo ln -s /etc/nginx/sites-available/syra-fresh /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

---

## 🗄️ MongoDB Backup & Maintenance

### Automated Backups

Create `/home/syra/backup-mongo.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/mongodb"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR

mongodump --uri="mongodb://syra_user:password@localhost:27017/syra_fresh_prod" \
  --out=$BACKUP_DIR/dump_$TIMESTAMP

# Keep only last 7 days
find $BACKUP_DIR -type d -name "dump_*" -mtime +7 -exec rm -rf {} \;
```

### Cron Job

```bash
# Add to crontab
0 2 * * * /home/syra/backup-mongo.sh >> /var/log/mongo-backup.log 2>&1
```

---

## 📊 Monitoring & Logging

### Application Logs

```bash
# Real-time logs
sudo tail -f /var/log/syra-fresh/app.log

# Last 100 lines
sudo tail -n 100 /var/log/syra-fresh/access.log
```

### Health Check

```bash
# Monitor endpoint
curl https://yourdomain.com/api/health

# Expected response
{"success": true, "service": "SYRA Fresh API", "status": "healthy"}
```

### Performance Monitoring

Install monitoring tools:

```bash
# CPU, Memory, Disk
sudo apt install sysstat

# Real-time monitoring
top
htop
iotop

# Network monitoring
netstat -tuln
```

---

## 🔄 Maintenance Tasks

### Weekly
- [ ] Check disk space
- [ ] Review error logs
- [ ] Verify backups exist
- [ ] Test API endpoints

### Monthly
- [ ] Update dependencies
- [ ] Review user feedback
- [ ] Analyze performance metrics
- [ ] Test disaster recovery

### Quarterly
- [ ] Security audit
- [ ] Database optimization
- [ ] Load testing
- [ ] Documentation review

---

## 🚨 Troubleshooting

### Backend won't start

```bash
# Check logs
sudo journalctl -u syra-backend -n 50

# Test Python
python3 -c "import flask; print('Flask OK')"

# Test MongoDB connection
mongosh --uri "mongodb://localhost:27017/syra_fresh_prod"
```

### Nginx errors

```bash
# Test configuration
sudo nginx -t

# Check syntax
sudo nginx -s reload

# View error log
sudo tail -f /var/log/nginx/syra-fresh-error.log
```

### High memory usage

```bash
# Restart service
sudo systemctl restart syra-backend

# Check process memory
ps aux | grep gunicorn

# Reduce workers if needed (edit service file)
```

---

## 🔐 Security Hardening

### Firewall Setup

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp  # Only for local

# Restrict API to local only
sudo ufw limit 5000/tcp from 127.0.0.1
```

### Fail2Ban Protection

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Configure for Nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
# Edit jail.local and add [sshd] and [nginx-http-auth]
```

### MongoDB Security

```bash
# Enable authentication
mongosh
> use admin
> db.createUser({
  user: "root",
  pwd: "strong-root-password",
  roles: ["root"]
})

# Restart with --auth flag
```

---

## 📈 Performance Optimization

### Enable Gzip Compression

In Nginx config:

```nginx
gzip on;
gzip_types text/css text/javascript application/json;
gzip_min_length 1000;
```

### Database Indexing

```bash
mongosh
> use syra_fresh_prod
> db.users.createIndex({"email": 1}, {unique: true})
> db.orders.createIndex({"user_id": 1, "created_at": -1})
> db.delivery_boys.createIndex({"status": 1})
```

### Connection Pooling

Already configured in Flask/PyMongo, but verify:

```python
# In extensions.py
_client = MongoClient(
    Config.MONGO_URI,
    maxPoolSize=50,
    minPoolSize=10,
)
```

---

## 🆘 Emergency Procedures

### Service Recovery

```bash
# If everything fails
sudo systemctl stop syra-backend
sudo systemctl stop nginx
sleep 5
sudo systemctl start mongodb
sleep 5
sudo systemctl start syra-backend
sudo systemctl start nginx
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop syra-backend

# Restore database
mongorestore --uri="mongodb://syra_user:password@localhost:27017/syra_fresh_prod" \
  /path/to/backup/dump_timestamp

# Restart
sudo systemctl start syra-backend
```

---

## 📞 Support Contacts

- **Technical Issues**: Check logs and restart services
- **Database Corruption**: Restore from backup
- **Performance Issues**: Check resource usage, optimize queries
- **Security Issues**: Review logs, check for suspicious activity

---

**Last Updated**: July 2024
**Tested On**: Ubuntu 20.04 LTS, MongoDB 5.0, Python 3.9, Nginx 1.18
