"""
@author: Yue Pan
@file: routes/assignment.py
@time: 2023/09/12
"""
import os
import uuid
from zipfile import ZipFile

from bson import ObjectId
from flask import Blueprint, request, send_file

from database import assignments
from utils.response import build_failure, build_success
from utils.autograder import generate_dataset_text, generate_autograder, generate_notebook
from config.generator import tmp_dir

assignment_bp = Blueprint("assignment", __name__)

# mkdir when tmp directory not exists
os.makedirs(tmp_dir, exist_ok=True)
autograder_dir = os.path.join(tmp_dir, "autograders")
os.makedirs(autograder_dir, exist_ok=True)


@assignment_bp.route("/data", methods=["POST"])
def api_assignment_data():
    try:
        assignment_id = request.json["id"] or ""
        file_type = request.json["format"] or "csv"
        seed = request.json["uscID"][0::2] if "uscID" in request.json.keys() else "None"

        assignment = list(assignments.find({
            "_id": ObjectId(assignment_id),
        }))[0]

        content = generate_dataset_text(assignment["dataset"], str(uuid.uuid1()),
                                        file_type=file_type, seed=seed, output_dir=tmp_dir)

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
                "state": "Draft",
            }).inserted_id
        return build_success(assignment_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@assignment_bp.route("/updateState/<assignment_id>", methods=["PUT"])
def api_assignment_update_state(assignment_id):
    try:
        state = request.json["state"] or "Draft"

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
                "state": "Published",
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


@assignment_bp.route("/autograder", methods=["POST"])
def api_assignment_generate_autograder():
    try:
        assignment_id = request.json["id"] or ""

        assignment = list(assignments.find({
            "_id": ObjectId(assignment_id),
        }))[0]

        assignment["_id"] = str(assignment["_id"])

        # Generate autograder.zip, solution and student template
        assignment_dir = os.path.join(autograder_dir, assignment_id)
        os.makedirs(assignment_dir, exist_ok=True)

        # Generate autograder.zip
        generate_autograder(assignment,
                            template_path=os.path.join("template", "autograder"),
                            output_path=os.path.join(assignment_dir, "autograder"),
                            zip_path=os.path.join(assignment_dir, "autograder.zip"))

        # Generate student template notebook
        generate_notebook(assignment["name"],
                          assignment["template"]["importCode"],
                          assignment["template"]["questions"],
                          output_dir=assignment_dir)

        # Return above 3 files as a zip
        file_paths = [
            os.path.join(assignment_dir, "autograder.zip"),
            os.path.join(assignment_dir, "autograder", "solution.ipynb"),
            os.path.join(assignment_dir, f"{assignment['name']}.ipynb")
        ]
        zip_path = os.path.join(autograder_dir, f"{assignment_id}.zip")
        with ZipFile(zip_path, "w") as zipf:
            for file in file_paths:
                zipf.write(file, os.path.basename(file))

        return send_file(zip_path, as_attachment=True, attachment_filename=f"{assignment['name']}.zip")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))
