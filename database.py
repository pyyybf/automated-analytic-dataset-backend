"""
@author: Yue Pan
@file: database.py
@time: 2023/09/12
"""
import pymongo
import mongodb_config

client = pymongo.MongoClient(
    f"mongodb+srv://{mongodb_config.username}:{mongodb_config.password}@{mongodb_config.cluster_name}.{mongodb_config.project_id}.mongodb.net/")
db = client[mongodb_config.db_name]
accounts = db["accounts"]
assignments = db["assignments"]
