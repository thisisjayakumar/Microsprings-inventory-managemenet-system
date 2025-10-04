# MSP-ERP Authentication Module

## Overview

The authentication module provides comprehensive user management, role-based access control, and security features specifically designed for the Microsprings Manufacturing ERP system.

## Features

### 🔐 Enhanced User Management
- Custom user model with MSP-ERP specific fields
- Employee ID, department, and shift management
- Network/IP-based access restrictions
- Session tracking and management

### 👥 Hierarchical Role System
- **Admin**: Full system access to all operations
- **Manager**: MO Management, Stock, Allocation, Reports, Part Master
- **Production Head**: All manager operations plus production oversight
- **Supervisor**: Process-specific tasks only
- **RM Store**: Process management, inventory, raw materials, and RM stock management
- **FG Store**: Process management and finished goods operations

### 🏭 Manufacturing-Specific Features
- Process supervisor assignments
- Worker engagement tracking (prevents double assignment)
- Department-based access control
- Shift-based time restrictions

### 🛡️ Security Features
- JWT token authentication
- Network restriction middleware
- Shift-based access control
- Session tracking and concurrent login prevention
- Rate limiting

## Models

### CustomUser
Extended Django user model with MSP-ERP fields:
- `email` (unique login field)
- `phone_number`
- Enhanced profile relationship

### UserProfile
Employee-specific information:
- `employee_id` (unique)
- `designation`
- `department` (choices: rm_store, coiling, tempering, plating, packing, fg_store, etc.)
- `shift` (I: 9AM-5PM, II: 5PM-2AM, III: 2AM-9AM)
- `is_engaged` (operator availability tracking)
- `allowed_ip_ranges` (network restrictions)

### Role
Hierarchical role system:
- `name` (admin, manager, production_head, supervisor, rm_store, fg_store)
- `hierarchy_level` (1=highest authority)
- `permissions` (JSON field with module-specific permissions)
- `restricted_departments` (department access control)

### ProcessSupervisor
Process-specific supervisor assignments:
- Links supervisors to specific processes
- Department-based assignments

### OperatorEngagement
Tracks operator assignments to prevent conflicts:
- `batch_id`, `process_step`, `machine_id`
- Start and estimated end times

### LoginSession
Session tracking for security:
- IP address and user agent tracking
- Login/logout timestamps
- Active session management

## API Endpoints

### Authentication
```
POST /api/auth/register/          # Register new user (Admin/Manager only)
POST /api/auth/login/             # JWT login with session tracking
POST /api/auth/logout/            # Logout with session cleanup
POST /api/auth/token/refresh/     # Refresh JWT token
```

### User Management
```
GET    /api/auth/users/                    # List users (paginated, filtered)
POST   /api/auth/users/                    # Create user
GET    /api/auth/users/{id}/               # Get user details
PUT    /api/auth/users/{id}/               # Update user
DELETE /api/auth/users/{id}/               # Delete user

GET    /api/auth/users/available-operators/     # Get available operators
GET    /api/auth/users/supervisors-by-department/ # Get supervisors by dept
POST   /api/auth/users/{id}/assign-role/         # Assign role to user
POST   /api/auth/users/{id}/engage-operator/     # Engage operator in process
POST   /api/auth/users/{id}/release-operator/    # Release operator
```

### Profile & Permissions
```
GET  /api/auth/profile/           # Current user profile
POST /api/auth/change-password/   # Change password
GET  /api/auth/permissions/       # Current user permissions
```

### Role Management
```
GET /api/auth/roles/              # List all roles
GET /api/auth/roles/hierarchy/    # Role hierarchy
```

### Process Supervisors
```
GET    /api/auth/process-supervisors/     # List process supervisors
POST   /api/auth/process-supervisors/     # Create assignment
PUT    /api/auth/process-supervisors/{id}/ # Update assignment
DELETE /api/auth/process-supervisors/{id}/ # Remove assignment
```

### Operator Engagements
```
GET /api/auth/operator-engagements/       # List current engagements
```

### Admin Features
```
POST /api/auth/bulk/role-assignment/      # Bulk role assignment
GET  /api/auth/dashboard/stats/           # Dashboard statistics
POST /api/auth/ip-restrictions/update/    # Update IP restrictions
GET  /api/auth/login-sessions/            # Login session tracking
```

## Permissions

### Role-Based Permissions
- `IsAdminOrManager`: Admin or Manager only
- `IsManagerOrAbove`: Manager and above (Admin, Manager, Production Head)
- `IsSupervisorOrAbove`: Supervisor and above (Admin, Manager, Production Head, Supervisor)
- `IsRMStoreOrAbove`: RM Store and above
- `IsFGStoreOrAbove`: FG Store and above

### Specialized Permissions
- `DepartmentAccessPermission`: Department-specific access
- `ProcessSupervisorPermission`: Process supervisor access
- `NetworkRestrictionPermission`: IP-based restrictions
- `OperatorEngagementPermission`: Worker management
- `ShiftBasedPermission`: Shift time restrictions

## Middleware

### Security Middleware
1. **NetworkRestrictionMiddleware**: Enforces IP restrictions
2. **ShiftRestrictionMiddleware**: Enforces shift-based access
3. **SessionTrackingMiddleware**: Tracks user sessions
4. **RoleBasedAccessMiddleware**: Adds role info to requests
5. **DepartmentAccessMiddleware**: Department access control
6. **OperatorEngagementMiddleware**: Worker conflict prevention
7. **APIRateLimitMiddleware**: Rate limiting (1000 req/hour)

## Management Commands

### Setup Commands
```bash
# Setup role hierarchy and permissions
python manage.py setup_roles

# Create admin user
python manage.py create_admin --email admin@microsprings.com --password admin123

# Create demo users for testing
python manage.py setup_demo_users --count 20
```

## Usage Examples

### 1. User Registration (Admin/Manager only)
```python
POST /api/auth/register/
{
    "username": "john.doe@microsprings.com",
    "email": "john.doe@microsprings.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "secure123",
    "password_confirm": "secure123",
    "employee_id": "EMP001",
    "designation": "Machine Operator",
    "department": "coiling",
    "shift": "I",
    "date_of_joining": "2024-01-15",
    "role_name": "operator"
}
```

### 2. Login with Network Tracking
```python
POST /api/auth/login/
{
    "email": "john.doe@microsprings.com",
    "password": "secure123"
}

Response:
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "full_name": "John Doe",
        "email": "john.doe@microsprings.com",
        "profile": {
            "employee_id": "EMP001",
            "department": "coiling",
            "shift": "I",
            "is_engaged": false
        },
        "primary_role": {
            "name": "operator",
            "hierarchy_level": 5
        }
    }
}
```

### 3. Engage Operator in Process
```python
POST /api/auth/users/1/engage-operator/
{
    "batch_id": "BATCH001",
    "process_step": "Coiling Setup",
    "machine_id": "COIL001",
    "estimated_end_time": "2024-01-15T14:00:00Z"
}
```

### 4. Get Available Operators
```python
GET /api/auth/users/available-operators/?department=coiling

Response:
[
    {
        "id": 1,
        "full_name": "John Doe",
        "employee_id": "EMP001",
        "department": "coiling",
        "shift": "I"
    }
]
```

## Security Considerations

### Network Restrictions
- Configure `allowed_ip_ranges` in user profiles
- Format: `["192.168.1.0/24", "10.0.0.0/8"]`
- Enforced by `NetworkRestrictionMiddleware`

### Shift Restrictions
- Operators restricted to their assigned shift hours
- Supervisors have extended access
- Admin/Manager: 24/7 access

### Operator Engagement
- Prevents double-assignment of operators
- Tracks current batch/process assignments
- Automatic conflict detection

### Session Management
- JWT tokens with refresh mechanism
- Session tracking with IP/User-Agent
- Concurrent login prevention

## Configuration

Add to Django settings:

```python
# Middleware (order matters)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.NetworkRestrictionMiddleware',
    'authentication.middleware.ShiftRestrictionMiddleware',
    'authentication.middleware.SessionTrackingMiddleware',
    'authentication.middleware.RoleBasedAccessMiddleware',
    'authentication.middleware.DepartmentAccessMiddleware',
    'authentication.middleware.OperatorEngagementMiddleware',
    'authentication.middleware.APIRateLimitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Custom user model
AUTH_USER_MODEL = 'authentication.CustomUser'

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Cache for permissions (Redis recommended)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

## Testing

The module includes comprehensive test coverage for:
- User registration and authentication
- Role-based permissions
- Network restrictions
- Shift-based access
- Operator engagement
- Session management

Run tests:
```bash
python manage.py test authentication
```

## Performance Optimizations

1. **Database Queries**: Optimized with `select_related` and `prefetch_related`
2. **Caching**: User roles and permissions cached for 5 minutes
3. **Pagination**: All list views support pagination
4. **Indexing**: Database indexes on frequently queried fields
5. **Bulk Operations**: Bulk role assignment support

## Monitoring

The module provides endpoints for monitoring:
- Active user sessions
- Operator engagement status
- Role distribution
- Department utilization
- Login patterns

Access via `/api/auth/dashboard/stats/` (Manager+ only)
