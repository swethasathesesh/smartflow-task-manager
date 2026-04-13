from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone

# --- BCRYPT SETUP (The Password Bouncer) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT SETUP (The VIP Wristband Factory) ---
SECRET_KEY = "smartflow_super_secret_key" # The secret stamp used to forge tokens!
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    # The wristband expires automatically after 1 hour for security
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        # Checks if the token is real and hasn't expired
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None # Returns nothing if the token is fake or expired