"""
@author: Yue Pan
@file: routes/account.py
@time: 2023/09/12
"""
from bson import ObjectId
from flask import Blueprint, request

from database import accounts
from utils import build_success, build_failure

account_blueprint = Blueprint('account', __name__)


@account_blueprint.route("/login", methods=["GET"])
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
                "firstName": user[0]["firstName"],
                "lastName": user[0]["lastName"],
                "role": user[0]["role"],
            })
        else:
            return build_failure("Incorrect username or password.")

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_blueprint.route("/getAll", methods=["GET"])
def api_account_get_all():
    try:
        user_list = list(accounts.find())

        return build_success(user_list)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_blueprint.route("/save", methods=["POST"])
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
                "password": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",  # sha(123456)
                "firstName": first_name,
                "lastName": last_name,
                "role": "TA",
            }).inserted_id
            return build_success(inserted_id)

    except Exception as e:
        print("Error: ", e.__class__.__name__, e)
        return build_failure(str(e))


@account_blueprint.route("/updatePwd", methods=["PUT"])
def api_account_update_pwd():
    try:
        account_id = request.json["id"] or None
        old_password = request.json["oldPassword"] or ""
        new_password = request.json["newPassword"] or "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"

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
