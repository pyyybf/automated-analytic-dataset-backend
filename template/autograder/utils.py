import requests
import sys
import subprocess
import numpy as np
import pandas as pd
import json
import re
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
                cell["source"][-1] += "\n"
                cell["source"].append("import matplotlib\n")
                cell["source"].append("matplotlib.use(\"Agg\")")
                for line in cell["source"]:
                    if line.startswith("import") or line.startswith("from"):
                        package = line.split(" ")[1].split(".")[0]
                        try:
                            __import__(package)
                        except ImportError:
                            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            elif "fetch_dataset" in metadata.keys():
                # Read dataset => Fetch from backend
                # cell["source"] = [
                #     "df = pd.read_csv(\"dataset.csv\")"
                # ]
                for index, line in enumerate(cell["source"]):
                    cell["source"][index] = re.sub(r"['\"]([^'\"]+\.csv)['\"]", "\"dataset.csv\"", line)
            elif "qid" in metadata.keys():
                qid = metadata["qid"]
                cell_mapping[qid] = idx
                if metadata["output_type"] == "dataframe":
                    # dataframe => csv
                    # cell["source"][-1] = f"{qid}.to_csv(\"{qid}_{suffix}.csv\")"
                    cell["source"].pop()
                    cell["source"].extend([
                        f"try:\n",
                        f"    {qid}.to_csv(\"{qid}_{suffix}.csv\")\n",
                        f"except:\n",
                        f"    df_err = pd.DataFrame({{\"CONVERTED_ERROR\": [True]}})\n",
                        f"    df_err.to_csv(\"{qid}_{suffix}.csv\")",
                    ])
                elif metadata["output_type"] == "dict":
                    # dict => json
                    #                     cell["source"][-1] = f"""import json
                    # with open("{qid}_{suffix}.json", "w") as fp:
                    #     json.dump({qid}, fp, indent=1)"""
                    cell["source"].pop()
                    cell["source"].extend([
                        f"import json\n",
                        f"try:\n",
                        f"    with open(\"{qid}_{suffix}.json\", \"w\") as fp:\n",
                        f"        json.dump({qid}, fp, indent=1)\n",
                        f"except:\n",
                        f"    dict_err = {{\"CONVERTED_ERROR\": True}}\n",
                        f"    with open(\"{qid}_{suffix}.json\", \"w\") as fp:\n",
                        f"        json.dump(dict_err, fp, indent=1)",
                    ])

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
def compare_number(val, sol, tolerance=0):
    return np.isclose(float(val), float(sol), atol=tolerance), f"Expected: {sol}, Actual: {val}"


def compare_df(val_path, sol_path):
    val = pd.read_csv(val_path)
    if "CONVERTED_ERROR" in val.columns:
        return False, "Output is not a dataframe"
    sol = pd.read_csv(sol_path)
    return val.equals(sol), f"Different dataframes"


def compare_dict(val_path, sol_path):
    with open(val_path, "r") as fp1:
        val = json.load(fp1)
    if "CONVERTED_ERROR" in val:
        return False, "Output is not a dictionary"
    with open(sol_path, "r") as fp2:
        sol = json.load(fp2)
    diff = []
    for key in sol.keys():
        if val[key] != sol[key]:
            diff.append(f"{key}: Expected: {sol[key]}, Actual: {val[key]}")
    return val == sol, "\n".join(diff)
