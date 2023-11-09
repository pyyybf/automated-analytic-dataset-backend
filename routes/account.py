"""
@author: Yue Pan
@file: routes/account.py
@time: 2023/09/12
"""
import os
import pandas as pd
import uuid

from bson import ObjectId
from flask import Blueprint, request

from config.generator import tmp_dir
from database import accounts
from utils import build_success, build_failure

account_bp = Blueprint("account", __name__)

SHA256_123456 = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"


@account_bp.route("/login", methods=["POST"])
def api_account_login():
    try:
        username = request.json["username"] or ""
        password = request.json["password"] or ""

        user = list(accounts.find({
            "username": username,
            "password": password,
        }))

        if len(user) > 0:
            return build_success({
                "id": user[0]["_id"],
                "username": user[0]["username"],
                "firstName": user[0]["firstName"],
                "lastName": user[0]["lastName"],
                "role": user[0]["role"],
            })
        else:
            return build_failure("Incorrect username or password.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/getAll", methods=["GET"])
def api_account_get_all():
    try:
        user_list = list(accounts.find())

        return build_success(user_list)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/save", methods=["POST"])
def api_account_save():
    try:
        account_id = request.json["id"] or None
        username = request.json["username"] or ""
        first_name = request.json["firstName"] or ""
        last_name = request.json["lastName"] or ""

        if account_id:
            accounts.update_one({"_id": ObjectId(account_id)}, {"$set": {
                "firstName": first_name,
                "lastName": last_name,
            }})
            return build_success(account_id)
        else:
            inserted_id = accounts.insert_one({
                "username": username,
                "password": SHA256_123456,
                "firstName": first_name,
                "lastName": last_name,
                "role": "TA",
            }).inserted_id
            return build_success(inserted_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/updatePwd", methods=["PUT"])
def api_account_update_pwd():
    try:
        account_id = request.json["id"] or None
        old_password = request.json["oldPassword"] or ""
        new_password = request.json["newPassword"] or SHA256_123456

        user_list = list(accounts.find({"_id": ObjectId(account_id), "password": old_password}))
        if len(user_list) > 0:
            accounts.update_one({"_id": ObjectId(account_id)}, {"$set": {
                "password": new_password,
            }})
            return build_success(account_id)
        else:
            return build_failure("Old password isn't valid.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/resetPwd", methods=["PUT"])
def api_account_reset_pwd():
    try:
        account_id = request.json["id"] or None

        user_list = list(accounts.find({"_id": ObjectId(account_id)}))
        if len(user_list) > 0:
            accounts.update_one({"_id": ObjectId(account_id)}, {"$set": {
                "password": SHA256_123456,
            }})
            return build_success(account_id)
        else:
            return build_failure("User doesn't exist.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/initPwd", methods=["PUT"])
def api_account_init_pwd():
    try:
        account_id = request.json["id"] or None

        user_list = list(accounts.find({"_id": ObjectId(account_id)}))
        if len(user_list) > 0:
            accounts.update_one({"_id": ObjectId(account_id)}, {"$set": {
                "password": SHA256_123456,
            }})
            return build_success(account_id)
        else:
            return build_failure("This user doesn't exist.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/delete/<account_id>", methods=["DELETE"])
def api_account_delete_by_id(account_id):
    try:
        accounts.delete_one({"_id": ObjectId(account_id)})
        return build_success(account_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/parseAccountFile", methods=["POST"])
def api_account_parse_account_file():
    try:
        file = request.files["file"]

        # save it to temporary directory
        filename = file.filename.split(".")
        filename = f"{'.'.join(filename[:-1])}_{uuid.uuid1()}.{filename[-1]}"
        file.save(f"{tmp_dir}/{filename}")

        # read and parse
        df = pd.read_excel(f"{tmp_dir}/{filename}")
        df.rename(columns={"Username/Email": "username", "Last Name": "lastName", "First Name": "firstName"},
                  inplace=True)
        account_list = df.to_dict("records")

        # delete it from temporary directory
        os.remove(f"{tmp_dir}/{filename}")

        return build_success(account_list)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_bp.route("/saveAll", methods=["POST"])
def api_account_save_all():
    try:
        account_list = request.json["accountList"]

        for account in account_list:
            account["password"] = SHA256_123456
            account["role"] = "TA"

        accounts.insert_many(account_list)

        return build_success()

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))
