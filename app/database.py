# app/database.py
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from .config import MONGO_URL

# 1. Establish the connection to the cloud database
# We include the 'certifi' patch here to prevent SSL handshake errors!
client = AsyncIOMotorClient(MONGO_URL, tlsCAFile=certifi.where())

# 2. Select the specific database for your application
# (MongoDB will automatically create this database the first time you save data to it)
db = client.task_management_pro

# 3. Define your Collections (where the actual data lives)
users_collection = db.get_collection("users")
tasks_collection = db.get_collection("tasks")

# 4. Diagnostic Function: To test if the connection is actually working
async def ping_server():
    try:
        # Sends a lightweight 'ping' to the database
        await client.admin.command('ping')
        print("✅ SUCCESS: Connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ ERROR: Database connection failed. Details: {e}")