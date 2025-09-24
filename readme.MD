# Smart Study Hub 2.0 🎓

[![Version](https://img.shields.io/badge/version-1.0.0--MVP-blue.svg)](./VERSION.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-green.svg)](https://mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-6.0+-red.svg)](https://redis.io)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> **Sistem Manajemen Pendidikan Modern** - Comprehensive educational management system dengan advanced analytics, real-time features, dan powerful export capabilities.

---

## 🌟 Overview

Smart Study Hub 2.0 adalah sistem manajemen pendidikan yang dirancang untuk memfasilitasi proses pembelajaran, ujian online, dan analitik pendidikan. Sistem ini mendukung multi-role (Admin, Teacher, Student) dengan fitur-fitur canggih untuk manajemen akademik yang efisien dan modern.

### ✨ Key Highlights
- 🚀 **Production Ready MVP** - Fully tested dan siap untuk deployment
- 📊 **Advanced Analytics** - Comprehensive performance tracking dan insights
- 📤 **Powerful Export System** - Multi-format exports dengan advanced query builder
- ⚡ **High Performance** - Redis caching dan optimized database queries
- 🔒 **Enterprise Security** - JWT authentication dengan role-based access control
- 🌐 **Real-time Updates** - WebSocket support untuk live notifications

---

## 🎯 Features

### 👥 User Management
- **Multi-role Authentication**: Admin, Teacher, Student dengan granular permissions
- **Profile Management**: Comprehensive user profiles dengan demographic data
- **Secure Authentication**: JWT-based dengan bcrypt password hashing
- **Role-based Access Control**: Fine-grained permission system

### 🏫 Academic Management
- **Class Organization**: Grade levels, expertise programs, dan class management
- **Subject Management**: Comprehensive subject definitions dan categorization
- **Academic Periods**: Semester/year management dengan flexible scheduling
- **Teaching Assignments**: Advanced teacher-class-subject assignment system

### 📝 Exam System
- **Question Banks**: Reusable question repository dengan advanced categorization
- **Flexible Exam Creation**: Multiple question types dan customizable settings
- **Real-time Exam Taking**: Live exam sessions dengan automatic scoring
- **Anti-cheating Features**: Tab switch detection dan session monitoring

### 📊 Analytics & Reporting
- **Student Performance Analytics**: Individual dan class-wide performance tracking
- **Teacher Analytics**: Teaching effectiveness dan class performance insights
- **Score Trend Analysis**: Historical performance tracking dengan visualizations
- **Subject Mastery Analysis**: Detailed subject-wise performance breakdown
- **Class Comparison**: Comparative analysis antar kelas dan periods

### 📤 Advanced Export System
- **Multi-format Support**: Excel, CSV, JSON, PDF exports
- **Advanced Query Builder**: Complex data filtering dengan nested joins
- **Custom Field Selection**: User-defined field selection untuk precise exports
- **Secure File Management**: Encrypted file storage dengan access logging

### ⚡ Performance & Scalability
- **Redis Caching**: Intelligent caching system untuk optimal performance
- **Background Tasks**: Asynchronous processing untuk heavy operations
- **Database Optimization**: Indexed queries dan optimized aggregations
- **WebSocket Support**: Real-time communication dan notifications

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.8+)
- **Database**: MongoDB 4.4+ dengan advanced aggregation pipelines
- **Caching**: Redis 6.0+ untuk session dan data caching
- **Authentication**: JWT dengan bcrypt password hashing
- **File Processing**: Pandas, OpenpyXL, ReportLab
- **WebSocket**: Real-time communication support

### Key Dependencies
```
fastapi>=0.104.0
motor>=3.3.0
redis>=4.5.0
pydantic>=2.0.0
pandas>=2.0.0
openpyxl>=3.1.0
reportlab>=4.0.0
bcrypt>=4.0.0
python-jose>=3.3.0
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB 4.4+
- Redis 6.0+
- Git

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-username/smart-study-hub-2.0.git
   cd smart-study-hub-2.0
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env dengan your configuration
   ```

4. **Database Setup**
   ```bash
   # Start MongoDB dan Redis
   # Create first admin user
   python create_first_admin.py
   
   # Create database indexes
   python scripts/create_analytics_indexes.py
   ```

5. **Run Application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access Application**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/system/health

---

## 📁 Project Structure

```
smart-study-hub-2.0/
├── app/
│   ├── api/v1/routes/          # API endpoints
│   ├── core/                   # Core functionality
│   │   ├── cache.py           # Redis caching
│   │   ├── database_schema.py # Database schema definitions
│   │   ├── export_handlers.py # Export system
│   │   └── security.py        # Authentication & authorization
│   ├── crud/                   # Database operations
│   ├── models/                 # Pydantic models
│   ├── services/              # Business logic
│   └── main.py                # FastAPI application
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
├── tests/                     # Test suite
├── requirements.txt           # Dependencies
├── RELEASE_NOTES.md          # Release documentation
├── VERSION.md                # Version information
├── DEPLOYMENT_GUIDE.md       # Deployment instructions
└── README.md                 # This file
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Application
APP_NAME="Smart Study Hub 2.0"
APP_VERSION="1.0.0-MVP"
DEBUG=False
SECRET_KEY="your-secret-key"

# Database
MONGODB_URL="mongodb://localhost:27017/smart_study_hub"
REDIS_URL="redis://localhost:6379/0"

# Security
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Performance
WORKERS=4
MAX_CONNECTIONS=100
```

### Database Collections

The system uses 12 core MongoDB collections:
- `users` - Authentication & roles
- `profiles` - User demographic data
- `classes` - Class organization
- `subjects` - Subject definitions
- `expertise_programs` - Department programs
- `academic_periods` - Semester management
- `teaching_assignments` - Teacher assignments
- `question_banks` - Question repository
- `exams` - Exam definitions
- `exam_sessions` - Student exam attempts
- `grades` - Grade calculations
- `activity_logs` - System audit logs

---

## 📊 API Documentation

### Core Endpoints

#### Authentication
```
POST /api/v1/auth/login          # User login
POST /api/v1/auth/refresh        # Token refresh
POST /api/v1/auth/logout         # User logout
```

#### User Management
```
GET  /api/v1/users               # List users
POST /api/v1/users               # Create user
GET  /api/v1/users/{id}          # Get user details
PUT  /api/v1/users/{id}          # Update user
```

#### Exam System
```
GET  /api/v1/exams               # List exams
POST /api/v1/exams               # Create exam
GET  /api/v1/exams/{id}/start    # Start exam session
POST /api/v1/exams/{id}/submit   # Submit exam
```

#### Analytics
```
GET  /api/v1/analytics/students/{id}/performance
GET  /api/v1/analytics/teachers/{id}/effectiveness
GET  /api/v1/analytics/classes/{id}/comparison
```

#### Export System
```
POST /api/v1/admin/exports       # Create export
GET  /api/v1/admin/exports/{id}  # Download export
GET  /api/v1/admin/exports/collections/relationships
```

### Interactive Documentation
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

---

## 🚀 Deployment

### Production Deployment

For detailed production deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).

#### Quick Production Setup
```bash
# Using Docker (recommended)
docker-compose up -d

# Or manual deployment
gunicorn -c gunicorn.conf.py app.main:app
```

#### Environment Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 20GB+ SSD
- **CPU**: 2+ cores

### Monitoring & Health Checks
```bash
# Health check endpoint
curl http://localhost:8000/api/v1/system/health

# System metrics
curl http://localhost:8000/api/v1/system/metrics

# Database status
curl http://localhost:8000/api/v1/system/db-status
```

---

## 📚 Documentation

### Available Documentation
- [Release Notes](./RELEASE_NOTES.md) - MVP release information
- [Version Information](./VERSION.md) - Version tracking dan roadmap
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Production deployment
- [API Documentation](./docs/ADMIN_EXPORT_API_DOCUMENTATION.md) - Detailed API guide
- [Quick Reference](./docs/ADMIN_EXPORT_QUICK_REFERENCE.md) - Quick start guide

### Additional Resources
- Database Schema: Detailed in `app/core/database_schema.py`
- Field Mapping: Available in `app/core/field_mapping.py`
- Export System: Documented in `docs/reports/`

---

## 📞 Support

### Getting Help
- **Documentation**: Check `/docs` endpoint untuk API documentation
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions untuk questions
- **Email**: Contact development team

### Community
- GitHub Repository: [smart-study-hub-2.0](https://github.com/your-username/smart-study-hub-2.0)
- Issue Tracker: Report bugs dan feature requests
- Wiki: Additional documentation dan tutorials

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Acknowledgments

- **Development Team**: Smart Study Hub engineering team
- **Beta Testers**: Educational institutions yang provided valuable feedback
- **Open Source Community**: Amazing tools dan libraries yang made this possible
- **Contributors**: All developers yang contributed to this project

---

## 🎯 What's Next?

### Upcoming Features (Post-MVP)
- Mobile application support
- Advanced AI-powered analytics
- Automated question generation
- Video conferencing integration
- Multi-language support
- Advanced reporting templates

### Roadmap
- **v1.1.0**: Enhanced UX & mobile support
- **v1.2.0**: AI features & advanced analytics
- **v2.0.0**: Microservices architecture & multi-tenant support

---

**🚀 Ready untuk Production!**

Smart Study Hub 2.0 MVP telah melalui extensive testing dan ready untuk production deployment. Sistem ini telah dioptimasi untuk performance, security, dan scalability.

For questions atau support, please contact the development team atau create an issue di GitHub repository.

---

*Built dengan ❤️ oleh Smart Study Hub Team*
