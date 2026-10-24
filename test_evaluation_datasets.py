import csv
import tempfile
import unittest
from pathlib import Path

from evaluation_datasets import load_datasets,read_method_rows


titles=("QMCPACK Orbital 144","FLASH Density 22","APS Kaz","Isabel PRECIP 24","Isabel QGRAUP 24","Miranda Velocity-x","Miranda Velocity-z","RTM Small 0360","Aramco 1800","SCALE-LETKF PRES","SCALE-LETKF T","CESM VD01 31","CESM UU 31","APS CSSI L0471","Nyx Baryon density 632","Nyx Temperature 632","APSU 004","APSU 006")


class EvaluationDatasetTests(unittest.TestCase):
    def test_manifest_contains_the_agreed_eighteen_fields(self):
        datasets=load_datasets()
        self.assertEqual(tuple(dataset["title"] for dataset in datasets),titles)
        by_title={dataset["title"]:dataset for dataset in datasets}
        self.assertEqual(by_title["APS Kaz"]["rel_eb_list"][2],.02)
        self.assertEqual(by_title["APSU 004"]["rel_eb_list"],by_title["APSU 006"]["rel_eb_list"])

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
