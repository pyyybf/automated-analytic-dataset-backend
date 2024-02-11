import unittest
import os
import json
from gradescope_utils.autograder_utils.decorators import weight


class TestFiles(unittest.TestCase):
    @weight(0)
    def test_submitted_files(self):
        """Check submitted files"""
        ipynb_files = []
        for root, dirs, files in os.walk("/autograder/submission"):
            for file in files:
                if file.endswith(".ipynb"):
                    ipynb_files.append(file)
        self.assertEqual(len(ipynb_files), 1, "Missing required Jupyter Notebook file!")
        print("All required files submitted!")

    @weight(0)
    def test_usc_id(self):
        """Check Student ID"""
        with open("/autograder/submission_metadata.json", "r") as fp:
            data = json.load(fp)
        usc_id = data["users"][0]["sid"]
        self.assertEqual(len(usc_id), 10, f"Invalid Student ID: {usc_id}")
        print(f"Student ID: {usc_id}")
