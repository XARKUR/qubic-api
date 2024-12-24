from pymongo import MongoClient
from config import MONGODB_URI

# MongoDB Connect
mongo_client = MongoClient(MONGODB_URI)
