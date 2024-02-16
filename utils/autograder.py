import os
import shutil
import subprocess
from zipfile import ZipFile
import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

existed_requirements = [
    "gradescope_utils",
    "nbconvert",
    "nbformat",
    "numpy",
    "pandas",
    "Requests",
    "packaging",
    "ipython",
    "ipykernel",
]


def generate_autograder(assignment_info, template_path="template", output_path="autograder", zip_path="autograder.zip"):
    # Assignment information
    assignment_id = assignment_info["_id"]
    assignment_name = assignment_info["name"]
    import_code = assignment_info["template"]["importCode"]
    questions = assignment_info["template"]["questions"]

    # Copy templates
    shutil.copytree(template_path, output_path, dirs_exist_ok=True)

    # Modify templates
    test_simple_path = os.path.join(output_path, "tests", "test_simple.py")
    replace_in_file(test_simple_path, "demo", assignment_name)
    replace_in_file(test_simple_path, "#assignment_id", assignment_id)

    run_autograder_path = os.path.join(output_path, "run_autograder")
    replace_in_file(run_autograder_path, "demo", assignment_name)

    # Generate requirements.txt
    add_requirements = []
    import_codes = import_code.strip().split("\n")
    for import_item in import_codes:
        if not (import_item.startswith("import") or import_item.startswith("from")):
            continue
        import_item = import_item.split(" ")
        req = import_item[1].split(".")[0]
        if req not in existed_requirements:
            add_requirements.append(req)
    with open(os.path.join(output_path, "requirements.txt"), "a") as fp:
        fp.write("\n".join(add_requirements))

    # Generate solution from questions
    generate_notebook(assignment_name, import_code, questions, output_dir=output_path, solution=True)

    # Generate test cases from questions
    test_case_content = generate_test_cases(assignment_name, questions)
    with open(os.path.join(output_path, "tests", "test_simple.py"), "a") as fp:
        fp.write("\n")
        fp.write(test_case_content)

    # Generate the autograder.zip
    generate_zip(source_path=output_path, output_path=zip_path)


def replace_in_file(file_path, old_s, new_s):
    with open(file_path, "r") as fp:
        content = fp.read()
        content = content.replace(old_s, new_s)
    with open(file_path, "w") as fp:
        fp.write(content)


def generate_notebook(assignment_name, import_code, questions, output_dir="autograder", solution=False):
    nb = new_notebook()

    # Title
    if solution:
        nb.cells.append(new_markdown_cell(f"# {assignment_name} - Solution"))
    else:
        nb.cells.append(new_markdown_cell(f"# {assignment_name}"))

    # Import packages
    import_code = import_code.split("\n")
    import_code = [item + "\n" for item in import_code[:-1]] + import_code[-1:]
    nb.cells.append(new_code_cell(import_code, metadata={"import_package": True}))

    # Fetch dataset
    if solution:
        nb.cells.append(new_code_cell([
            f"df = pd.read_csv(\"{assignment_name} - Dataset.csv\")\n",
            "df.head()"
        ], metadata={"fetch_dataset": True}))
    else:
        nb.cells.append(new_code_cell(["df = ..."], metadata={"fetch_dataset": True}))

    # Start questions
    for qid, question in enumerate(questions, start=1):
        # Markdown cell: Question title & description
        nb.cells.append(new_markdown_cell(
            f"## Question {qid}: {question['title']}\n\n{question['description']}"
        ))
        for sub_qid, sub_question in enumerate(question["subquestions"], start=1):
            # Markdown cell: Sub-question description
            nb.cells.append(new_markdown_cell(
                f"**Q{qid}.{sub_qid}** ({sub_question['points']} points) {sub_question['description']}"
            ))
            # Code cell: Sub-question code / placeholder
            nb.cells.append(new_code_cell(sub_question["code"] if solution else [
                f"q_{qid}_{sub_qid} = ...\n",
                f"q_{qid}_{sub_qid}"
            ], metadata={
                "qid": f"q_{qid}_{sub_qid}",
                "output_type": sub_question["outputType"]
            }))

    # Write into jupyter notebook
    if solution:
        nbformat.write(nb, os.path.join(output_dir, "solution.ipynb"))
    else:
        nbformat.write(nb, os.path.join(output_dir, f"{assignment_name}.ipynb"))


def generate_test_cases(assignment_name, questions):
    test_cases = []
    for qid, question in enumerate(questions, start=1):
        for sub_qid, sub_question in enumerate(question["subquestions"], start=1):
            test_case = create_test_func(assignment_name, qid, sub_qid, sub_question)
            test_case = "".join([f"    {line}\n" for line in test_case])
            test_cases.append(test_case)
    return "\n".join(test_cases)


def create_test_func(assignment_name, qid, sub_qid, sub_question):
    lines = [
        f"@weight({sub_question['points']})",
        f"@number(\"{qid}.{sub_qid}\")",
        f"def test_{qid}_{sub_qid}(self):",
        f"    \"\"\"Test Question {qid}.{sub_qid}\"\"\"",
    ]
    if sub_question["outputType"] == "number":
        lines.extend([
            f"    val = get_cell_output(self.nb_stu, self.cell_mapping_stu[\"q_{qid}_{sub_qid}\"])",
            f"    sol = get_cell_output(self.nb_sol, self.cell_mapping_sol[\"q_{qid}_{sub_qid}\"])",
            f"    self.assertTrue(compare_number(val, sol, {sub_question['tolerance']}))",
        ])
    elif sub_question["outputType"] == "dataframe":
        lines.append(
            f"    self.assertTrue(compare_df(\"q_{qid}_{sub_qid}_{assignment_name}.csv\", \"q_{qid}_{sub_qid}_solution.csv\"))"
        )
    elif sub_question["outputType"] == "dict":
        lines.append(
            f"    self.assertTrue(compare_dict(\"q_{qid}_{sub_qid}_{assignment_name}.json\", \"q_{qid}_{sub_qid}_solution.json\"))"
        )
    return lines


def generate_zip(source_path="autograder", output_path="autograder.zip"):
    with ZipFile(output_path, "w") as zipf:
        parent_dir = os.path.abspath(source_path)
        for root, dirs, files in os.walk(parent_dir):
            for file in files:
                file_path = os.path.join(root, file)
                in_zip_path = os.path.relpath(file_path, parent_dir)
                zipf.write(file_path, in_zip_path)
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                in_zip_dir_path = os.path.relpath(dir_path, parent_dir) + "/"
                zipf.write(dir_path, in_zip_dir_path)


def generate_dataset_text(dataset_info, file_id, file_type="csv", seed="None", output_dir="tmp"):
    code = dataset_info["code"]
    import_code = dataset_info["importCode"]
    field_list = dataset_info["fieldList"]

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
    if file_type == "csv":
        file_path = os.path.join(output_dir, "data_{sys.argv[1]}.csv")
        call_code += f"df.to_csv(f\"{file_path}\", index=False)\n"
    elif file_type == "json":
        file_path = os.path.join(output_dir, "data_{sys.argv[1]}.json")
        call_code += f"df.to_json(f\"{file_path}\", orient=\"records\")"

    script_path = os.path.join(output_dir, f"generate_df_{file_id}.py")
    with open(script_path, "w", encoding="utf-8") as target:
        target.write(f"import sys\n{import_code}\n\n\n{code}\n\n\n{call_code}")

    # run generate_df.py to generate data file in temporary file directory
    process = subprocess.Popen(["python", script_path, file_id])
    process.wait()
    process.terminate()

    # read data file as string
    dataset_path = os.path.join(output_dir, f"data_{file_id}.{file_type}")
    with open(dataset_path, "r", encoding="utf-8") as source:
        content = source.read()

    # delete temporary file
    os.remove(script_path)
    os.remove(dataset_path)

    return content


if __name__ == "__main__":
    assignment_info = {
        "_id": "65c8cb581d0320f7ed85650a",
        "name": "Zip Test Demo",
        "template": {
            "importCode": "# Please import all the necessary Python packages in this cell\nimport numpy as np\nimport pandas as pd\nimport statsmodels.api as sm",
            "questions": [
                {
                    "title": "Statistics",
                    "description": "",
                    "subquestions": [
                        {
                            "description": "Calculate average X1.",
                            "code": "q_1_1 = df[\"X1\"].mean()\nq_1_1",
                            "outputType": "number",
                            "tolerance": 1,
                            "points": 20,
                        },
                        {
                            "description": "Calculate average X2.",
                            "code": "q_1_2 = df[\"X2\"].mean()\nq_1_2",
                            "outputType": "number",
                            "tolerance": 1,
                            "points": 20,
                        },
                    ]
                },
                {
                    "title": "One-Hot Encoding",
                    "description": "",
                    "subquestions": [
                        {
                            "description": "Convert the category column X6 into binary dummy variables (1 or 0) (Have \"Yellow\" be the default value).",
                            "code": """df["Blue"] = pd.get_dummies(df["X6"])["Blue"].astype(int)
df["Red"] = pd.get_dummies(df["X6"])["Red"].astype(int)
df = df.drop("X6", axis=1)
q_2_1 = df
q_2_1""",
                            "outputType": "dataframe",
                            "points": 30,
                        },
                    ]
                },
                {
                    "title": "StatsModels",
                    "description": "",
                    "subquestions": [
                        {
                            "description": "Using statsmodels, perform a regression for Y using X1 through X5 and your dummy variables. Use `model.params.to_dict()` to display the params as a dict below.",
                            "code": """model = sm.OLS(df["Y"], sm.add_constant(df.drop("Y", 1)))
model = model.fit()
q_3_1 = model.params.to_dict()
q_3_1""",
                            "outputType": "dict",
                            "points": 20,
                        },
                        {
                            "description": "Display the R-square.",
                            "code": "q_3_2 = model.rsquared\nq_3_2",
                            "outputType": "number",
                            "tolerance": 0.001,
                            "points": 10,
                        },
                    ]
                },
            ]
        },
        "state": "draft",
    }
    # Generate autograder.zip
    generate_autograder(assignment_info,
                        template_path="../template",
                        output_path="../tmp/autograder",
                        zip_path="../tmp/autograder.zip")
    # Generate student template notebook
    generate_notebook(assignment_info["name"],
                      assignment_info["template"]["importCode"],
                      assignment_info["template"]["questions"],
                      output_dir="../tmp/")
    # Generate solution notebook
    generate_notebook(assignment_info["name"],
                      assignment_info["template"]["importCode"],
                      assignment_info["template"]["questions"],
                      output_dir="../tmp/",
                      solution=True)
