"""
@author: Yue Pan
@file: main.py
@time: 2023/07/10
"""
import warnings
import json

from flask import Flask
from flask_cors import CORS
from bson.json_util import ObjectId

from routes.account import account_bp
from routes.assignment import assignment_bp


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)


app = Flask(__name__)
app.json_encoder = MyEncoder
CORS(app)

app.register_blueprint(account_bp, url_prefix='/api/account')
app.register_blueprint(assignment_bp, url_prefix='/api/assignment')


@app.route("/")
def goodbye_world():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(port=8080, host="127.0.0.1", debug=False)
    warnings.filterwarnings("ignore")
