import json
import unittest
from gradescope_utils.autograder_utils.decorators import weight, number

from utils import fetch_dataset, preprocess_nb, execute_nb, get_cell_output, compare_number, compare_df, compare_dict


class TestDemo(unittest.TestCase):
    def setUp(self):
        # Get the student's id
        with open("/autograder/submission_metadata.json", "r") as fp:
            data = json.load(fp)
        usc_id = data["users"][0]["sid"]

        # Fetch the dataset to dataset,csv
        fetch_dataset("#assignment_id", usc_id, output_path="dataset.csv")

        # Preprocess the notebooks and get the index mapping of question cells
        self.cell_mapping_stu = preprocess_nb("demo.ipynb")
        self.cell_mapping_sol = preprocess_nb("solution.ipynb")

        # Read and execute the two notebooks
        self.nb_stu = execute_nb("demo.ipynb")
        self.nb_sol = execute_nb("solution.ipynb")
