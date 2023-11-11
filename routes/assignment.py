"""
@author: Yue Pan
@file: routes/assignment.py
@time: 2023/09/12
"""
import os
import subprocess
import uuid

from bson import ObjectId
from flask import Blueprint, request

from database import assignments
from utils import build_failure, build_success
from config import generator

GENERATE_CODE = {
    # df.to_csv(f"/tmp/data_{sys.argv[1]}.csv", index=False)
    "csv": f"df.to_csv(f\"{generator.tmp_dir}/data_{{sys.argv[1]}}.csv\", index=False)\n",
    # df.to_json(f"/tmp/data_{sys.argv[1]}.json", orient="records")
    "json": f"df.to_json(f\"{generator.tmp_dir}/data_{{sys.argv[1]}}.json\", orient=\"records\")",
}

assignment_bp = Blueprint("assignment", __name__)

# mkdir when tmp directory not exists
if not os.path.exists(generator.tmp_dir):
    os.mkdir(generator.tmp_dir)


@assignment_bp.route("/data", methods=["POST"])
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
        field_list = assignment["fieldList"]

        # get function name
        main_func = code[code.find("def ") + 4:code.find("(")] if "def " in code else "generate_ad"

        # add code to call the function
        call_code = f"ad = {main_func}({seed})\n"
        call_code += "df = ad.predictor_matrix\n"
        call_code += "df[ad.response_vector_name or \"Y\"] = ad.response_vector\n"

        # drop invisible columns
        invisible_columns = []
        for column in field_list:
            if column["invisible"]:
                invisible_columns.append(f'"{column["name"]}"')
        if len(invisible_columns) > 0:
            call_code += f"df = df.drop([{', '.join(invisible_columns)}], axis=1)\n"

        # add code to generate data file: csv/json
        call_code += GENERATE_CODE[file_type]

        # generate an uuid
        file_id = str(uuid.uuid1())

        with open(f"{generator.tmp_dir}/generate_df_{file_id}.py", "w", encoding="utf-8") as target:
            target.write(f"import sys\n{import_code}\n\n\n{code}\n\n\n{call_code}")

        # run generate_df.py to generate data file in temporary file directory
        process = subprocess.Popen(["python", f"{generator.tmp_dir}/generate_df_{file_id}.py", file_id])
        process.wait()
        process.terminate()

        # read data file as string
        with open(f"{generator.tmp_dir}/data_{file_id}.{file_type}", "r", encoding="utf-8") as source:
            content = source.read()

        # ? delete temporary file
        os.remove(f"{generator.tmp_dir}/generate_df_{file_id}.py")
        os.remove(f"{generator.tmp_dir}/data_{file_id}.{file_type}")

        return build_success(content, "text/csv" if file_type == "csv" else "application/json")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@assignment_bp.route("/save", methods=["POST"])
def api_assignment_save():
    try:
        assignment_id = request.json["id"] or None
        code = request.json["code"] or "def generate_ad():\n    ad = AnalyticsDataframe(1000, 6)\n    return ad"
        import_code = request.json["importCode"] or "from analyticsdf.analyticsdataframe import AnalyticsDataframe"
        name = request.json["name"] or "Assignment"
        number_of_rows = request.json["numberOfRows"] or 1000
        field_list = request.json["fieldList"] or []
        covariance_matrix = request.json["covarianceMatrix"] or {}

        if assignment_id:
            assignments.update_one({"_id": ObjectId(assignment_id)}, {"$set": {
                "code": code,
                "importCode": import_code,
                "name": name,
                "numberOfRows": number_of_rows,
                "fieldList": field_list,
                "covarianceMatrix": covariance_matrix,
            }})
            return build_success(assignment_id)
        else:
            inserted_id = assignments.insert_one({
                "code": code,
                "importCode": import_code,
                "name": name,
                "numberOfRows": number_of_rows,
                "fieldList": field_list,
                "covarianceMatrix": covariance_matrix,
                "state": "draft",
            }).inserted_id
            return build_success(inserted_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@assignment_bp.route("/updateState/<assignment_id>", methods=["PUT"])
def api_assignment_update_state(assignment_id):
    try:
        state = request.json["state"] or "draft"

        assignments.update_one({"_id": ObjectId(assignment_id)}, {"$set": {
            "state": state,
        }})
        return build_success(assignment_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@assignment_bp.route("/getAll", methods=["GET"])
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


@assignment_bp.route("/get/<assignment_id>", methods=["GET"])
def api_assignment_get_by_id(assignment_id):
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


@assignment_bp.route("/delete/<assignment_id>", methods=["DELETE"])
def api_account_delete_by_id(assignment_id):
    try:
        assignments.delete_one({"_id": ObjectId(assignment_id)})
        return build_success(assignment_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))
