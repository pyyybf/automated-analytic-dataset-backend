"""
@author: Yue Pan
@file: main.py
@time: 2023/07/10
"""

import os
import subprocess
import warnings
import json
import uuid

import pymongo

from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from bson.json_util import ObjectId

import mongodb_config


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)


# temporary file directory
TMP_DIR = "./tmp_generator"  # dev
# TMP_DIR = "/tmp"  # prod

GENERATE_CODE = {
    # df.to_csv(f"/tmp/data_{sys.argv[1]}.csv", index=False)
    "csv": f"df.to_csv(f\"{TMP_DIR}/data_{{sys.argv[1]}}.csv\", index=False)\n",
    # df.to_json(f"/tmp/data_{sys.argv[1]}.json", orient="records")
    "json": f"df.to_json(f\"{TMP_DIR}/data_{{sys.argv[1]}}.json\", orient=\"records\")",
}

app = Flask(__name__)
app.json_encoder = MyEncoder
CORS(app)

client = pymongo.MongoClient(
    f"mongodb+srv://{mongodb_config.username}:{mongodb_config.password}@{mongodb_config.cluster_name}.{mongodb_config.project_id}.mongodb.net/")
db = client[mongodb_config.db_name]
accounts = db["accounts"]
assignments = db["assignments"]


def build_success(content, mimetype="application/json"):
    result = {
        "success": True,
        "message": "",
        "content": content
    }
    return Response(jsonify(result).response, mimetype=mimetype)


def build_failure(message):
    result = {
        "success": False,
        "message": message,
        "content": {}
    }
    return Response(jsonify(result).response, mimetype="application/json")


@app.route("/")
def goodbye_world():
    return app.send_static_file("index.html")


# generator
API_ASSIGNMENT_PRE = "/api/assignment"


@app.route(f"{API_ASSIGNMENT_PRE}/data", methods=["POST"])
def api_assignment_data():
    try:
        assignment_id = request.json["id"] or ""
        file_type = request.json["format"] or "csv"
        seed = request.json["uscID"][0::2] if "uscID" in request.json.keys() else "None"

        assignment = list(assignments.find({
            "_id": ObjectId(assignment_id),
        }))[0]

        code = assignment["code"]
        import_code = assignment["importCode"]

        # get function name
        main_func = code[code.find("def ") + 4:code.find("(")] if "def " in code else "generate_ad"

        # add code to call the function
        call_code = f"ad = {main_func}({seed})\n"
        call_code += "df = ad.predictor_matrix\n"
        call_code += "df[ad.response_vector_name or \"Y\"] = ad.response_vector\n"

        # add code to generate data file: csv/json
        call_code += GENERATE_CODE[file_type]

        # generate an uuid
        file_id = str(uuid.uuid1())

        with open(f"{TMP_DIR}/generate_df_{file_id}.py", "w", encoding="utf-8") as target:
            target.write(f"import sys\n{import_code}\n\n\n{code}\n\n\n{call_code}")

        # run generate_df.py to generate data file in temporary file directory
        process = subprocess.Popen(["python", f"{TMP_DIR}/generate_df_{file_id}.py", file_id])
        process.wait()
        process.terminate()

        # read data file as string
        with open(f"{TMP_DIR}/data_{file_id}.{file_type}", "r", encoding="utf-8") as source:
            content = source.read()

        # ? delete temporary file
        os.remove(f"{TMP_DIR}/generate_df_{file_id}.py")
        os.remove(f"{TMP_DIR}/data_{file_id}.{file_type}")

        return build_success(content, "text/csv" if file_type == "csv" else "application/json")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@app.route(f"{API_ASSIGNMENT_PRE}/save", methods=["POST"])
def api_assignment_save():
    try:
        assignment_id = request.json["id"] or None
        code = request.json["code"] or "def generate_ad():\n    ad = AnalyticsDataframe(1000, 6)\n    return ad"
        import_code = request.json["importCode"] or "from analyticsdf.analyticsdataframe import AnalyticsDataframe"
        name = request.json["name"] or "Assignment"
        field_list = request.json["fieldList"] or {}

        if assignment_id:
            assignments.update_one({"_id": ObjectId(assignment_id)}, {"$set": {
                'code': code,
                'importCode': import_code,
                'name': name,
                'fieldList': field_list,
            }})
            return build_success(assignment_id)
        else:
            inserted_id = assignments.insert_one({
                'code': code,
                'importCode': import_code,
                'name': name,
                'fieldList': field_list,
                'state': 'draft',
            }).inserted_id
            return build_success(inserted_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@app.route(f"{API_ASSIGNMENT_PRE}/updateState/<assignment_id>", methods=["PUT"])
def api_assignment_update_state(assignment_id):
    try:
        state = request.json["state"] or "draft"

        assignments.update_one({"_id": ObjectId(assignment_id)}, {"$set": {
            'state': state,
        }})
        return build_success(assignment_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@app.route(f"{API_ASSIGNMENT_PRE}/getAll", methods=["GET"])
def api_assignment_get_all():
    try:
        role = request.args.get("role") or None
        if role:
            assignment_list = list(assignments.find())
        else:
            assignment_list = list(assignments.find({
                "state": "published",
            }))
        return build_success(assignment_list)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@app.route(f"{API_ASSIGNMENT_PRE}/get/<assignment_id>", methods=["GET"])
def api_assignment_get(assignment_id):
    try:
        assignment_list = list(assignments.find({
            "_id": ObjectId(assignment_id),
        }))
        if len(assignment_list) > 0:
            return build_success(assignment_list[0])
        else:
            return build_failure("Can't find the assignment.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


# account
API_ACCOUNT_PRE = "/api/account"


@app.route(f"{API_ACCOUNT_PRE}/login", methods=["GET"])
def api_account_login():
    try:
        username = request.args.get("username") or ""
        password = request.args.get("password") or ""

        user = list(accounts.find({
            "username": username,
            "password": password,
        }))

        if len(user) > 0:
            return build_success({
                "username": user[0]["username"],
                "role": user[0]["role"],
            })
        else:
            return build_failure("Incorrect username or password.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


if __name__ == "__main__":
    app.run(port=8080, host="127.0.0.1", debug=False)
    warnings.filterwarnings("ignore")
