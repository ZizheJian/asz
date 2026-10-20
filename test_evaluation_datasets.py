import csv
import tempfile
import unittest
from pathlib import Path

from evaluation_datasets import load_datasets,read_method_rows


titles=("QMCPACK Orbital 144","RTM 0750","Isabel PRECIP 24","Isabel QRAIN 24","Miranda Velocity-x","Miranda Density","Aramco 1800","SCALE-LETKF PRES","SCALE-LETKF T","CESM Q 31","CESM UU 31","Nyx Baryon density 632","Nyx Dark-matter density 632","APS CSSI L0471","APSU 004","E 017","APSU 006")


class EvaluationDatasetTests(unittest.TestCase):
    def test_manifest_contains_the_agreed_seventeen_fields(self):
        datasets=load_datasets()
        self.assertEqual(tuple(dataset["title"] for dataset in datasets),titles)

    def test_single_dataset_legacy_csv_does_not_require_data_path(self):
        with tempfile.TemporaryDirectory(prefix="asz-evaluation-test-") as directory:
            root=Path(directory)
            path=root/"legacy.csv"
            with open(path,"w",newline="",encoding="utf-8") as output_file:
                writer=csv.DictWriter(output_file,fieldnames=("REL_EB","METHOD","BR","PSNR"),lineterminator="\n")
                writer.writeheader()
                for index in range(5):
                    writer.writerow({"REL_EB":10**(-index-1),"METHOD":"sz3","BR":index+1,"PSNR":index+30})
            dataset={"title":"Legacy","results":{"sz3":path.name}}
            self.assertEqual(len(read_method_rows(root,dataset,"sz3")),5)


if __name__=="__main__":
    unittest.main()
