# 🚀 Task Management Pro - Modern Task Management System

A full-stack task management application built with FastAPI, featuring JWT authentication, real-time task tracking, and comprehensive user management.

## ✨ Features

### 🔐 Authentication & Security
- User registration with email OTP verification
- JWT token-based authentication (access + refresh tokens)
- Secure password hashing with bcrypt
- Automatic token refresh on expiry
- Protected API endpoints
- Environment variable configuration

### 👥 User Management
- Complete user profiles with bio
- Profile picture upload with thumbnails
- User settings and preferences stored in database
- Password change functionality
- Email and phone verification

### ✅ Task Management
- Create, read, update, and delete tasks
- Kanban board with drag-and-drop
- Task prioritization (Low/Medium/High/Urgent)
- Status tracking (Todo/In Progress/Completed)
- Due date and time tracking
- Task tags and notes
- Task search and filtering
- Task statistics and analytics

### 📊 Dashboard & Analytics
- Real-time task statistics
- Completion rate tracking
- Overdue task alerts
- Task count by status
- Completion tracking per day

### 🎨 User Interface
- Modern responsive design
- Drag-and-drop task management
- Real-time updates
- Toast notifications
- Mobile-friendly
- Bootstrap 5 styling

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.119.0 |
| **Language** | Python 3.10+ |
| **Database** | MongoDB Atlas |
| **Authentication** | JWT (python-jose) |
| **Password Hashing** | bcrypt |
| **Email Service** | aiosmtplib |
| **Image Processing** | Pillow (PIL) |
| **Frontend** | Bootstrap 5, Vanilla JavaScript |


## 📋 Prerequisites

- Python 3.10 or higher
- MongoDB Atlas account (or local MongoDB)
- Email service credentials (Gmail or SMTP)
- pip/pip3

## 🚀 Quick Start

### 1. Clone the Repository

```sh 
git clone https://github.com/yourusername/user-task-management.git
cd user-task-management
```

### 2. Environment Setup

Create a `.env` file in the project root (see `ENV_SETUP_GUIDE.md` for details):

```bash
# MongoDB Configuration
MONGODB_USERNAME=your_username
MONGODB_PASSWORD=your_password
MONGODB_CLUSTER=cluster0.mongodb.net
DATABASE_NAME=task_manager-pro

# Security & Authentication
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Configuration (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# OTP Settings
OTP_LENGTH=6
OTP_EXPIRY_MINUTES=10
MAX_OTP_ATTEMPTS=3

# Development Mode (set to False for production)
DEVELOPMENT_MODE=True
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python main.py
# or
uvicorn main:app --reload
```

### 5. Access the Application

- **Frontend:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Database Check:** http://localhost:8000/health/db

## 📁 Project Structure
```text
user-task-management/
├── app/
│   ├── init.py
│   ├── main.py                # FastAPI application entry point               
│   ├── config.py              # Configuration and environment variables
│   ├── database.py            # MongoDB connection and setup
│   ├── models.py              # Pydantic models and schemas
│   ├── auth/
│   │   ├── init.py
│   │   ├── routes.py          # Authentication endpoints
│   │   ├── jwt_handler.py     # JWT token management
│   │   ├── dependencies.py    # Auth dependencies
│   │   └── utils.py           # Password hashing, OTP generation
│   ├── users/
│   │   ├── init.py
│   │   ├── routes.py          # User management endpoints
│   │   ├── models.py          # User data models
│   │   └── services.py        # User business logic
│   ├── tasks/
│   │   ├── init.py
│   │   ├── routes.py          # Task management endpoints
│   │   ├── models.py          # Task data models
│   │   └── services.py        # Task business logic
│   ├── ai/
│   │   ├── init.py
│   │   ├── task_analyzer.py   # AI task analysis
│   │   ├── categorizer.py     # AI categorization
│   │   └── estimator.py       # Time estimation
│   └── utils/
│       ├── init.py
│       ├── email_service.py   # Email sending functionality
│       └── validators.py      # Custom validators
├── tests/
│   ├── init.py
│   ├── test_auth.py
│   ├── test_users.py
│   └── test_tasks.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
```

## 🔑 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user with email |
| POST | `/api/auth/verify-otp` | Verify OTP sent to email |
| POST | `/api/auth/login` | Login and receive JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/forgot-password` | Request password reset |
| POST | `/api/auth/reset-password` | Reset password with token |
| POST | `/api/auth/resend-otp` | Resend OTP to email |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/me` | Get current user profile |
| PUT | `/api/users/me` | Update current user profile |
| DELETE | `/api/users/me` | Delete current user account |
| PATCH | `/api/users/me/password` | Change password |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create new task |
| GET | `/api/tasks` | List all user tasks (with filters) |
| GET | `/api/tasks/{task_id}` | Get specific task |
| PUT | `/api/tasks/{task_id}` | Update task |
| DELETE | `/api/tasks/{task_id}` | Delete task |
| POST | `/api/tasks/{task_id}/ai-analyze` | Get AI suggestions for task |

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch
```bash
git checkout -b <branch-name>
```
3. Commit changes
```bash
git commit -m <branch-name>
```
4. Push to branch
```bash
git push origin <branch-name>
```
5. Open Pull Request

## 📝 License

This project is for educational purpose.
