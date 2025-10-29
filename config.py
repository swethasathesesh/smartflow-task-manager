from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
import certifi
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from environment variables with fallbacks
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_CLUSTER = os.getenv("MONGODB_CLUSTER")
DATABASE_NAME = os.getenv("DATABASE_NAME")

print(f"Connecting to MongoDB as user: {MONGODB_USERNAME}")

# Encode password for URL (handles special characters)
encoded_password = quote_plus(MONGODB_PASSWORD)
uri = f"mongodb+srv://{MONGODB_USERNAME}:{encoded_password}@{MONGODB_CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0"

print("MongoDB URI constructed successfully")

try:
    # Create a new client and connect to the server with SSL certificate
    # Using certifi for proper SSL certificate verification
    client = MongoClient(
        uri, 
        server_api=ServerApi('1'),
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000  # 5 second timeout
    )
    
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    
    db = client.get_database(DATABASE_NAME)
    
    users_collection = db.get_collection("users")
    tasks_collection = db.get_collection("tasks")
    password_reset_tokens_collection = db.get_collection("password_reset_tokens")
    task_history_collection = db.get_collection("task_history")
    comments_collection = db.get_collection("comments")
    settings_history_collection = db.get_collection("settings_history")
    task_attachments_collection = db.get_collection("task_attachments")
    task_templates_collection = db.get_collection("task_templates")
    categories_collection = db.get_collection("categories")
    
    # Create indexes for performance (if they don't exist already)
    try:
        users_collection.create_index("email", unique=True)
        users_collection.create_index("username", unique=True)
        tasks_collection.create_index("user_id")
        tasks_collection.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
        tasks_collection.create_index("parent_task_id")
        password_reset_tokens_collection.create_index("token", unique=True)
        password_reset_tokens_collection.create_index("email")
        password_reset_tokens_collection.create_index("expires_at", expireAfterSeconds=0)
        task_history_collection.create_index("task_id")
        task_history_collection.create_index("user_id")
        comments_collection.create_index("task_id")
        comments_collection.create_index("user_id")
        settings_history_collection.create_index("user_id")
        settings_history_collection.create_index("created_at")
        task_attachments_collection.create_index("task_id")
        task_attachments_collection.create_index("user_id")
        task_templates_collection.create_index("user_id")
        categories_collection.create_index("user_id")
        categories_collection.create_index("name")
        print("Database indexes created successfully!")
    except Exception as idx_error:
        print(f"Index creation warning: {idx_error}")
        pass  # Indexes might already exist
        
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    print("Please check your MongoDB credentials in .env file")
    # Create dummy collections to prevent NoneType errors
    class DummyCollection:
        def __getattr__(self, name):
            raise Exception("MongoDB connection failed. Please check your credentials.")
    users_collection = DummyCollection()
    tasks_collection = DummyCollection()
    password_reset_tokens_collection = DummyCollection()
    task_history_collection = DummyCollection()
    comments_collection = DummyCollection()
    settings_history_collection = DummyCollection()
    task_attachments_collection = DummyCollection()
    task_templates_collection = DummyCollection()
    categories_collection = DummyCollection()
    raise