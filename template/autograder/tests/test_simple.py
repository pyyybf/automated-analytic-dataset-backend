import json
import unittest
from gradescope_utils.autograder_utils.decorators import weight, number

from utils import *


class TestDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the student's id
        with open("/autograder/submission_metadata.json", "r") as fp:
            data = json.load(fp)
        usc_id = data["users"][0]["sid"]

        # Fetch the dataset to dataset,csv
        fetch_dataset("#assignment_id", usc_id, output_path="dataset.csv")

        # Preprocess the notebooks and get the index mapping of question cells
        cls.cell_mapping_stu = preprocess_nb("demo.ipynb")
        cls.cell_mapping_sol = preprocess_nb("solution.ipynb")

        # Read and execute the two notebooks
        cls.nb_stu = execute_nb("demo.ipynb")
        cls.nb_sol = execute_nb("solution.ipynb")
