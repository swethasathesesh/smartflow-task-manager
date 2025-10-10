# 🚀 Task Management System with AI Integration

A modern, feature-rich REST API built with FastAPI for managing users and tasks, complete with email-based authentication, OTP verification, password recovery, containerization, and AI-powered task intelligence.

## ✨ Features

### 🔐 Authentication & Security
- User registration with email verification
- Time-based OTP (TOTP) generation and validation
- JWT token-based authentication (access + refresh tokens)
- Secure password hashing with bcrypt
- Forgot password with email-based token reset
- Protected API endpoints with role-based access

### 👥 User Profile
- Complete CRUD operations for user profiles
- Email verification workflow
- Profile updates and account management
- User preferences and settings

### ✅ Task Management
- Create, read, update, and delete tasks
- Task categorization (Work/Personal)
- Priority levels (High/Medium/Low)
- Status tracking (Todo/In Progress/Completed/Archived)
- Due date management
- User-specific task isolation

### 🤖 AI-Powered Features
- Automatic task categorization using AI
- Smart priority suggestions based on task content
- Estimated time-to-completion predictions
- Natural language processing for task analysis

### 🐋 Containerization & Deployment
- Docker support for consistent environments
- Docker Compose for multi-container orchestration
- Production-ready deployment configurations
- Free-tier deployment options (Render/Railway/Fly.io)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.104+ |
| **Language** | Python 3.10+ |
| **Database** | MongoDB Atlas (Free M0 Cluster) |
| **Authentication** | JWT + PyOTP |
| **Email Service** | Amazon SES / Brevo |
| **AI Integration** | OpenAI GPT-5-nano / Google Gemini Flash |
| **Containerization** | Docker + Docker Compose |
| **Deployment** | Render.com / Railway / Fly.io |


## 📋 Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- MongoDB Atlas account
- Email service credentials (Amazon SES or Brevo)
- OpenAI or Google Gemini API key (optional, for AI features)
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```sh 
git clone https://github.com/yourusername/user-task-management.git
cd user-task-management
```

### 2. Environment Setup

Create a `.env` file in the project root:

```text
# Application Settings
APP_NAME=User Task Management
APIDEBUG=True
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=task_management

# Email Service (Amazon SES)
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USERNAME=your-ses-smtp-username
EMAIL_PASSWORD=your-ses-smtp-password
EMAIL_FROM=noreply@yourdomain.com

# OTP Settings
OTP_EXPIRE_MINUTES=10
OTP_LENGTH=6

# AI Integration
# OPENAI_API_KEY=sk-your-openai-api-key 
# GOOGLE_API_KEY=your-google-gemini-api-key
# AI_PROVIDER=openai  #switch to openai or gemini

# Deployment
PORT=8000
HOST=0.0.0.0
```

### 3. Local Development

Install dependencies
```bash
pip install -r requirements.txt
```
Run the application
```bash
uvicorn app.main:app –reload
```

### 4. Docker Development

Build and run with Docker Compose
```bash
docker-compose up –build
```
Run in detached mode
```bash
docker-compose up -d
```
Stop containers
```bash
docker-compose down
```

### 5. Access the Application

- **API Documentation (Swagger UI):** http://localhost:8000/docs
- **Alternative Documentation (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

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
