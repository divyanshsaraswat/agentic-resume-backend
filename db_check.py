import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

try:
    print(f"Connecting to MongoDB...")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
