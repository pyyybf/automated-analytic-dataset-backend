"""
@author: Yue Pan
@file: init_db.py
@time: 2023/09/10
"""

import pymongo
import json

from config import mongodb

client = pymongo.MongoClient(
    f"mongodb+srv://{mongodb.username}:{mongodb.password}@{mongodb.cluster}.{mongodb.project}.mongodb.net/")

# drop database if exists
if mongodb.db_name in client.list_database_names():
    print(f"The database {mongodb.db_name} exists.")
    client.drop_database(mongodb.db_name)

db = client[mongodb.db_name]

with open("./static/database.json", "r") as fp:
    db_data = json.load(fp)

# set password
for account in db_data["accounts"]:
    account["password"] = ""

for collection_name in db_data:
    print(f"Insert collection {collection_name}")
    collection = db[collection_name]
    collection.insert_many(db_data[collection_name])

client.close()
