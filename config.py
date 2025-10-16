
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://sarathmrtvm:<db_password>@cluster0.gg6brmy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.get_database("task_manager-pro")

users_collection = db.get_collection("users")
tasks_collection = db.get_collection("tasks")