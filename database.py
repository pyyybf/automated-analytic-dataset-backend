"""
@author: Yue Pan
@file: database.py
@time: 2023/09/12
"""
import pymongo
from config import mongodb

client = pymongo.MongoClient(
    f"mongodb+srv://{mongodb.username}:{mongodb.password}@{mongodb.cluster}.{mongodb.project}.mongodb.net/")
db = client[mongodb.db_name]

# collections
accounts = db["accounts"]
assignments = db["assignments"]
