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
accounts_collection = db["accounts"]
assignments_collection = db["assignments"]

accounts = [
    {
        "username": "admin",
        "firstName": "admin",
        "lastName": "",
        "password": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
        "role": "INSTRUCTOR"
    },
    {
        "username": "brucewil@usc.edu",
        "firstName": "Bruce",
        "lastName": "Wilcox",
        "password": "",
        "role": "INSTRUCTOR"
    },
    {
        "username": "ypan4655@usc.edu",
        "firstName": "Yue",
        "lastName": "Pan",
        "password": "",
        "role": "TA"
    },
    {
        "username": "xizhulin@usc.edu",
        "firstName": "Xizhu",
        "lastName": "Lin",
        "password": "",
        "role": "TA"
    },
    {
        "username": "cwei7837@usc.edu",
        "firstName": "Chentao",
        "lastName": "Wei",
        "password": "",
        "role": "TA"
    },
]
accounts_collection.insert_many(accounts)

with open("./template/sample_template.json") as fp:
    sample_template = json.load(fp)

assignments = [
    {
        "name": "Module 4 Homework",
        "dataset": {
            "code": 'def generate_ad(seed=None):\n    ad = AnalyticsDataframe(1000, 1, ["uni"], "Y", seed=seed)\n    \n    ad.update_predictor_uniform("uni", 0, 1)\n    \n    predictor_name_list = ["uni"]\n    beta = [0, 0]\n    eps_var = 0\n    ad.generate_response_vector_linear(predictor_name_list=predictor_name_list, beta=beta, epsilon_variance=eps_var)\n    return ad',
            "importCode": "from analyticsdf.analyticsdataframe import AnalyticsDataframe",
            "numberOfRows": 1000,
            "fieldList": [
                {
                    "type": "UNIFORM",
                    "name": "uni",
                    "lowerBound": 0,
                    "upperBound": 1,
                    "invisible": False,
                },
                {
                    "type": "RESPONSE_VECTOR_LINEAR",
                    "name": "Y",
                    "predictorList": {"uni": {"checked": True}},
                    "intercept": 0,
                    "epsilonVariance": 0,
                    "exponent": "",
                    "invisible": False,
                },
            ],
            "covarianceMatrix": {},
        },
        "template": sample_template,
        "state": "Published",
    },
    {
        "name": "Assignment #2",
        "dataset": {
            "code": 'def generate_ad(seed=None):\n    ad = AnalyticsDataframe(1000, 2, ["ca", "ca_weight"], "Y", seed=seed)\n    \n    ad.update_predictor_categorical("ca", ["aaa", "bbb"], [0.25, 0.75])\n    \n    # create a new predictor column, change categorical value into numerical value\n    categorical_mapping_ca = {"aaa": 1, "bbb": 0}\n    ad.predictor_matrix["ca_weight"] = ad.predictor_matrix.replace({"ca": categorical_mapping_ca}, inplace=False)["ca"]\n    \n    predictor_name_list = ["ca_weight"]\n    beta = [7, 12]\n    eps_var = 0\n    ad.generate_response_vector_linear(predictor_name_list=predictor_name_list, beta=beta, epsilon_variance=eps_var)\n    ad.response_vector = np.exp(0.02 * ad.response_vector)\n    return ad',
            "importCode": "from analyticsdf.analyticsdataframe import AnalyticsDataframe\nimport numpy as np",
            "numberOfRows": 1000,
            "fieldList": [
                {
                    "type": "CATEGORICAL", "name": "ca",
                    "categoryList": [{"name": "aaa", "prob": 1}, {"name": "bbb", "prob": "3"}],
                    "invisible": False,
                },
                {
                    "type": "CATEGORICAL_TO_NUMERICAL",
                    "name": "ca_weight",
                    "target": "ca",
                    "categoricalMapping": {"aaa": "1", "bbb": 0},
                    "inplace": False,
                    "invisible": False,
                },
                {
                    "type": "RESPONSE_VECTOR_LINEAR",
                    "name": "Y",
                    "predictorList": {"ca_weight": {"checked": True, "beta": "12"}},
                    "intercept": "7",
                    "epsilonVariance": 0,
                    "exponent": "0.02",
                    "invisible": False,
                },
            ],
            "covarianceMatrix": {},
        },
        "template": sample_template,
        "state": "Draft",
    },
    {
        "name": "Assignment #3",
        "dataset": {
            "code": 'def generate_ad():\n    ad = AnalyticsDataframe(1000, 6)\n    return ad',
            "importCode": "from analyticsdf.analyticsdataframe import AnalyticsDataframe",
            "numberOfRows": 1000,
            "fieldList": [],
            "covarianceMatrix": {},
        },
        "template": sample_template,
        "state": "Draft",
    },
]
assignments_collection.insert_many(assignments)

client.close()
