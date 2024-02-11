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
from utils.response import build_failure, build_success
from config.generator import tmp_dir

GENERATE_CODE = {
    # df.to_csv(f"/tmp/data_{sys.argv[1]}.csv", index=False)
    "csv": f"df.to_csv(f\"{tmp_dir}/data_{{sys.argv[1]}}.csv\", index=False)\n",
    # df.to_json(f"/tmp/data_{sys.argv[1]}.json", orient="records")
    "json": f"df.to_json(f\"{tmp_dir}/data_{{sys.argv[1]}}.json\", orient=\"records\")",
}

assignment_bp = Blueprint("assignment", __name__)

# mkdir when tmp directory not exists
if not os.path.exists(tmp_dir):
    os.mkdir(tmp_dir)


@assignment_bp.route("/data", methods=["POST"])
def api_assignment_data():
    try:
        assignment_id = request.json["id"] or ""
        file_type = request.json["format"] or "csv"
        seed = request.json["uscID"][0::2] if "uscID" in request.json.keys() else "None"

        assignment = list(assignments.find({
            "_id": ObjectId(assignment_id),
        }))[0]

        code = assignment["dataset"]["code"]
        import_code = assignment["dataset"]["importCode"]
        field_list = assignment["dataset"]["fieldList"]

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

        # script_path = f"{tmp_dir}/generate_df_{file_id}.py"
        script_path = os.path.join(tmp_dir, f"generate_df_{file_id}.py")
        with open(script_path, "w", encoding="utf-8") as target:
            target.write(f"import sys\n{import_code}\n\n\n{code}\n\n\n{call_code}")

        # run generate_df.py to generate data file in temporary file directory
        process = subprocess.Popen(["python", script_path, file_id])
        process.wait()
        process.terminate()

        # read data file as string
        # dataset_path = f"{tmp_dir}/data_{file_id}.{file_type}"
        dataset_path = os.path.join(tmp_dir, f"data_{file_id}.{file_type}")
        with open(dataset_path, "r", encoding="utf-8") as source:
            content = source.read()

        # delete temporary file
        os.remove(script_path)
        os.remove(dataset_path)

        return build_success(content, "text/csv" if file_type == "csv" else "application/json")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@assignment_bp.route("/save", methods=["POST"])
def api_assignment_save():
    try:
        assignment_id = request.json["id"] or None
        name = request.json["name"] or "Assignment"
        dataset = {
            "code": request.json["dataset"][
                        "code"] or "def generate_ad():\n    ad = AnalyticsDataframe(1000, 6)\n    return ad",
            "importCode": request.json["dataset"][
                              "importCode"] or "from analyticsdf.analyticsdataframe import AnalyticsDataframe",
            "numberOfRows": request.json["dataset"]["numberOfRows"] or 1000,
            "fieldList": request.json["dataset"]["fieldList"] or [],
            "covarianceMatrix": request.json["dataset"]["covarianceMatrix"] or {},
        }
        template = {
            "importCode": request.json["template"]["importCode"] or "",
            "questions": request.json["template"]["questions"] or []
        }

        if assignment_id:
            assignments.update_one({"_id": ObjectId(assignment_id)}, {"$set": {
                "name": name,
                "dataset": dataset,
                "template": template,
            }})
        else:
            assignment_id = assignments.insert_one({
                "name": name,
                "dataset": dataset,
                "template": {
                    "importCode": "",
                    "questions": [],
                },
                "state": "draft",
            }).inserted_id
        return build_success(assignment_id)

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
        if role == "TA" or role == "INSTRUCTOR":
            assignment_list = list(assignments.find())
        else:
            assignment_list = list(assignments.find({
                "state": "published",
            }, {
                "dataset": 0,
                "template": 0,
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
def api_assignment_delete_by_id(assignment_id):
    try:
        assignments.delete_one({"_id": ObjectId(assignment_id)})
        return build_success(assignment_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))
