"""
Email Configuration
Loads settings from environment variables with fallback defaults
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP Server Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your-email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your-app-password")

# Email Settings
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Task Management System")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))  # seconds

# OTP Settings
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "3"))

# Development Mode (set to True to print OTP to console instead of sending email)
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"

"""
SETUP INSTRUCTIONS:

For Gmail:
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security > 2-Step Verification > App passwords
   - Generate a password for "Mail"
3. Use this App Password in EMAIL_PASSWORD above

For other providers:
1. Check your email provider's SMTP settings
2. Update SMTP_SERVER and SMTP_PORT accordingly
3. Use your email and password (or app password if required)

Security Notes:
- Never commit real credentials to version control
- Consider using environment variables in production
- Use app passwords instead of regular passwords when available
"""
