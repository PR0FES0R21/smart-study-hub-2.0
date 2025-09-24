# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Smart Study Hub is a FastAPI-based school management system with real-time exam capabilities, built using MongoDB and Redis. The system supports multiple user roles (students, teachers, admins) with comprehensive academic management features including online exams, grade tracking, and analytics.

## Common Development Commands

### Starting the Application
```bash
# Development server (with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers

# Using Docker
docker build -t smart-study-hub .
docker run -p 8000:8000 smart-study-hub
```

### Background Services
```bash
# Start Celery worker for background tasks
celery -A app.core.celery_app worker --loglevel=info

# Start Redis server (required for WebSocket and caching)
redis-server

# MongoDB connection (configured via environment variables)
# See .env.example for database configuration
```

### Testing
```bash
# Run specific test files
python -m pytest tests/test_score_analytics.py -v
python -m pytest tests/test_exam_validation_improvements.py -v

# Run tests with specific pattern
python -m pytest tests/ -k "test_score" -v

# Run individual test scripts (for development/debugging)
python tests/test_websocket.html  # WebSocket test page
python tests/simple_mass_login.js  # Load testing script
```

### Database Operations
```bash
# Create first admin user
python create_first_admin.py

# Generate password hash (utility)
python generate_password_hash.py

# Data import/manipulation scripts
python tests/add_subjects.py
python tests/tambah_data_siswa.py
python tests/delete_teachers.py
```

## Architecture Overview

### High-Level Structure
The application follows a clean architecture pattern with clear separation of concerns:

- **`app/main.py`** - FastAPI application entry point with WebSocket Redis bridge
- **`app/api/v1/`** - API routes and endpoints organized by feature
- **`app/core/`** - Core application services (database, config, security, caching)
- **`app/crud/`** - Data access layer with MongoDB operations
- **`app/schemas/`** - Pydantic models for request/response validation
- **`app/tasks/`** - Celery background tasks for heavy operations
- **`app/middleware/`** - Custom middleware (onboarding, etc.)
- **`app/utils/`** - Utility functions and helpers

### Key Architectural Patterns

#### 1. Normalized Database Design with Smart Caching
The system uses MongoDB with a normalized approach, leveraging ObjectId references between collections. Key entities:
- **Core Entities**: users, profiles, expertise_programs, subjects, classes
- **Academic Operations**: academic_periods, teaching_assignments, coordination_assignments
- **Exam System**: question_banks, exams, exam_sessions, question_sets
- **Analytics**: Built-in score analytics and reporting

#### 2. Intelligent Redis Caching Strategy
Cache invalidation is handled intelligently - when data changes, related cached data is automatically invalidated and refreshed. Cache keys follow patterns like:
- `users:ids:*` - User-related caches
- `analytics:*` - Analytics caches
- Custom patterns per feature

#### 3. Real-Time WebSocket Architecture
- **WebSocket Manager**: Handles connections with Redis bridge for scaling
- **Room-based Communication**: Supports exam rooms and general notifications
- **Redis Pub/Sub**: Enables multi-instance WebSocket communication
- **Connection States**: Proper lifecycle management with detailed logging

#### 4. Background Task Processing
Uses Celery with Redis broker for:
- **Excel Import/Export**: Bulk user operations with progress tracking
- **Analytics Computation**: Heavy statistical calculations
- **Academic Cycle Tasks**: Period transitions and bulk operations
- **Score Analytics**: Grade calculations and reporting

#### 5. Multi-Role Permission System
Role-based access control with dynamic permissions:
- **Students**: Access to exams, grades, profiles
- **Teachers**: Question banks, exam creation, grading
- **Admins**: Full system access, user management
- **Department Heads**: Department-specific management

### Critical Data Relationships

#### Teaching Assignments as Central Hub
The `teaching_assignments` collection is crucial - it connects:
- Teachers to their classes and subjects
- Academic periods to active teaching
- Exam permissions and access control
- Analytics scope and filtering

#### Exam System Flow
1. **Question Banks** → Created by teachers, organized by subject/difficulty
2. **Question Sets** → Curated collections from question banks
3. **Exams** → Teaching assignment + question sets + settings
4. **Exam Sessions** → Individual student attempts with real-time monitoring
5. **Score Analytics** → Automated analysis and reporting

#### Profile-User Separation
Users contain authentication/roles, profiles contain personal/academic data. This separation allows:
- Clean role-based access control
- Flexible profile data per user type
- Efficient user queries without heavy profile joins

## Development Guidelines

### Database Operations
- Always use the CRUD functions in `app/crud/` rather than direct database calls
- Implement proper cache invalidation when modifying data
- Use aggregation pipelines for complex queries (see examples in `crud_users.py`)
- Handle ObjectId validation before database operations

### WebSocket Development
- Use the established WebSocket manager in `app/core/websocket.py`
- Implement proper error handling and logging (see `ws.py` for patterns)
- Handle connection lifecycle properly (connect/disconnect/error states)
- Use room-based messaging for targeted communication

### Background Tasks
- Follow the SafeEventLoopManager pattern for async operations in Celery
- Use proper database connection management (DatabaseManager context)
- Implement progress tracking for long-running tasks
- Handle task failures gracefully with proper error reporting

### Testing Approach
- Individual test files focus on specific features (exam validation, score analytics)
- Load testing scripts available for WebSocket and API endpoints
- Test data manipulation scripts in `tests/` directory
- WebSocket testing via `test_websocket.html`

### API Development
- Follow the established router pattern in `app/api/v1/routes/`
- Use Pydantic schemas for all input/output validation
- Implement proper error handling with HTTP status codes
- Include DataTables support for admin interfaces where needed

### Configuration Management
Environment variables are centrally managed in `app/core/config.py`:
- Database connections (MongoDB, Redis)
- JWT configuration
- File storage (R2/Cloudflare)
- Feature flags and timeouts

## Important Implementation Details

### Cache Key Patterns
When implementing cache invalidation, follow established patterns:
- Use wildcards for pattern-based invalidation
- Invalidate related data (e.g., user changes should invalidate analytics)
- Set appropriate TTL values for different data types

### WebSocket Message Handling
- All messages should include `type` field for routing
- Implement proper JSON validation
- Log all connection events with session tracking
- Handle disconnections gracefully

### Database Aggregation
The system heavily uses MongoDB aggregation pipelines for:
- User listings with role-specific data
- Teaching assignment summaries
- Score calculations and analytics
- Complex filtering and search operations

### Error Handling
- Use structured logging with clear patterns
- Include session/user context in all logs
- Implement proper HTTP status codes
- Handle MongoDB ObjectId validation consistently

### File Operations
- Temporary file handling in `temp_uploads/` directory
- Excel import/export with progress tracking
- Profile picture upload to R2 storage
- Proper cleanup of temporary resources
