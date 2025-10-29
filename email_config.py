"""
Email Configuration
Loads settings from environment variables with fallback defaults
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP Server Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Email Settings
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT"))  # seconds

# OTP Settings
OTP_LENGTH = int(os.getenv("OTP_LENGTH"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES"))
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS"))

# Development Mode (set to True to print OTP to console instead of sending email)
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE").lower() == "true"

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
