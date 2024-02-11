import requests
import sys
import subprocess
import numpy as np
import pandas as pd
import json
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


def fetch_dataset(assignment_id, usc_id, output_path="dataset.csv"):
    url = "https://backend-dot-automated-dataset-generation.wl.r.appspot.com/api/assignment/data"
    params = {
        "id": assignment_id,
        "format": "csv",
        "uscID": usc_id
    }
    response = requests.post(url, json=params)

    if response.status_code == 200:
        csv_text = response.json()["content"]
        with open(output_path, "w") as fp:
            fp.write(csv_text)
    else:
        raise Exception(f"Fail to fetch the dataset for student {usc_id}!")


def preprocess_nb(nb_path):
    with open(nb_path, "r") as fp:
        nb = json.load(fp)
    suffix = nb_path.split(".")[0]  # Submission name or solution

    cell_mapping = {}
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            metadata = cell["metadata"]
            if "import_package" in metadata.keys():
                for line in cell["source"]:
                    if line.startswith("import") or line.startswith("from"):
                        package = line.split(" ")[1].split(".")[0]
                        try:
                            __import__(package)
                        except ImportError:
                            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            elif "fetch_dataset" in metadata.keys():
                # Read dataset => Fetch from backend
                cell["source"] = [
                    "df = pd.read_csv(\"dataset.csv\")"
                ]
            elif "qid" in metadata.keys():
                qid = metadata["qid"]
                cell_mapping[qid] = idx
                if metadata["output_type"] == "dataframe":
                    # dataframe => csv
                    cell["source"][-1] = f"{qid}.to_csv(\"{qid}_{suffix}.csv\")"
                elif metadata["output_type"] == "dict":
                    # dict => json
                    cell["source"][-1] = f"""import json
with open("{qid}_{suffix}.json", "w") as fp:
    json.dump({qid}, fp, indent=1)"""

    with open(nb_path, "w") as fp:
        json.dump(nb, fp, indent=4)
    return cell_mapping


def execute_nb(nb_path):
    with open(nb_path, "r") as fp:
        nb = nbformat.read(fp, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb)
    return nb


def get_cell_output(nb, index):
    cell = nb["cells"][index]
    for output in cell.outputs:
        # if output.output_type == "stream":
        #     return output.text
        if output.output_type == "execute_result":
            return output.data["text/plain"]


# Comparing tools
def compare_number(number1, number2, tolerance=0):
    return np.isclose(float(number1), float(number2), atol=tolerance)


def compare_df(df_path1, df_path2):
    df1 = pd.read_csv(df_path1)
    df2 = pd.read_csv(df_path2)
    return df1.equals(df2)


def compare_dict(dict_path1, dict_path2):
    with open(dict_path1, "r") as fp1:
        dict1 = json.load(fp1)
    with open(dict_path2, "r") as fp2:
        dict2 = json.load(fp2)
    return dict1 == dict2
