from flask import Flask, request, send_file, jsonify
from flask_restful import Resource, Api

from tempfile import gettempdir
from pathlib import Path
import os
import zipfile
import json
import sys
import io
import glob
import re

tmp_location = Path(gettempdir()) / "RLUnit_hub"
os.makedirs(tmp_location, exist_ok=True)

class Agent(Resource):
    def get(self, agent_name):
        data_location = tmp_location/agent_name
        archive_regex = re.compile("(%s[\\\/](?:\w+[\\\/])*\w+\.\w+)$"
                                       % (agent_name))
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in data_location.glob("**/*"):
                result = archive_regex.search(str(file))
                if result and result.group(1):
                    file_name = result.group(1)
                    archive.write(file, file_name)

        memory_file.seek(0)
        file_name = "%s.zip" % agent_name
        return send_file(memory_file, attachment_filename=file_name,
                         as_attachment=True)
    
    def put(self, agent_name, trial_idx):
        if 'results' not in request.files:
            return "There is no results file attached"

        result_zip = request.files["results"]
        with zipfile.ZipFile(result_zip, "r") as archive:
            archive.extractall(tmp_location)

        return "done"

app = Flask(__name__)
api = Api(app)

api.add_resource(Agent,
                 "/results/agent/<string:agent_name>",
                 "/results/agent/<string:agent_name>/<int:trial_idx>")

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5003)
