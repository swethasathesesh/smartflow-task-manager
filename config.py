from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
import certifi

# ⚠️ IMPORTANT: Replace this with your actual MongoDB password
# If your password has special characters like @, #, !, etc., they will be automatically encoded
MONGODB_PASSWORD = "sarath0899"  # ← REPLACE THIS WITH YOUR REAL PASSWORD
MONGODB_USERNAME = "sarathmrtvm"

# Encode password for URL (handles special characters)
encoded_password = quote_plus(MONGODB_PASSWORD)
uri = f"mongodb+srv://{MONGODB_USERNAME}:{encoded_password}@cluster0.gg6brmy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server with SSL certificate
# Using certifi for proper SSL certificate verification
client = MongoClient(
    uri, 
    server_api=ServerApi('1'),
    tlsCAFile=certifi.where()
)

db = client.get_database("task_manager-pro")

users_collection = db.get_collection("users")
tasks_collection = db.get_collection("tasks")