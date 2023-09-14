"""
@author: Yue Pan
@file: utils.py
@time: 2023/09/12
"""
from flask import Response, jsonify


def build_success(content=None, mimetype="application/json"):
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
