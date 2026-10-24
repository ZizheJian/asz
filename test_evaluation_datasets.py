import csv
import tempfile
import unittest
from pathlib import Path

from evaluation_datasets import compression_time,load_datasets,preprocessing_time,read_method_rows


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

    def write_rows(self,path,bounds,data_path="/data/right.f32"):
        with open(path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=("DATA_PATH","REL_EB","METHOD","BR","PSNR"),lineterminator="\n")
            writer.writeheader()
            for index,bound in enumerate(bounds):
                writer.writerow({"DATA_PATH":data_path,"REL_EB":bound,"METHOD":"asz","BR":index+1,"PSNR":index+30})

    def test_result_bounds_must_match_manifest(self):
        with tempfile.TemporaryDirectory(prefix="asz-evaluation-test-") as directory:
            root=Path(directory)
            path=root/"results.csv"
            self.write_rows(path,(.1,.01,.001,.0001,.0002))
            dataset={"title":"Field","data_path":"/data/right.f32","rel_eb_list":[.1,.01,.001,.0001,.00001],"results":{"asz":path.name}}
            with self.assertRaisesRegex(ValueError,"relative error bounds do not match"):
                read_method_rows(root,dataset,"asz")

    def test_duplicate_result_bounds_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="asz-evaluation-test-") as directory:
            root=Path(directory)
            path=root/"results.csv"
            self.write_rows(path,(.1,.01,.001,.0001,.0001))
            dataset={"title":"Field","data_path":"/data/right.f32","rel_eb_list":[.1,.01,.001,.0001,.00001],"results":{"asz":path.name}}
            with self.assertRaisesRegex(ValueError,"duplicate"):
                read_method_rows(root,dataset,"asz")

    def test_result_data_path_must_match_manifest(self):
        with tempfile.TemporaryDirectory(prefix="asz-evaluation-test-") as directory:
            root=Path(directory)
            path=root/"results.csv"
            self.write_rows(path,(.1,.01,.001,.0001,.00001),"/data/wrong.f32")
            dataset={"title":"Field","data_path":"/data/right.f32","rel_eb_list":[.1,.01,.001,.0001,.00001],"results":{"asz":path.name}}
            with self.assertRaisesRegex(ValueError,"found 0"):
                read_method_rows(root,dataset,"asz")

    def test_data_range_scan_is_compression(self):
        row={"COMPRESSION_TIME":"2.5","PREPROCESSING_TIME":"1.0","DATA_RANGE_TIME":"0.25"}
        self.assertEqual(compression_time(row),2.75)
        self.assertEqual(preprocessing_time(row),1.0)
        self.assertEqual(compression_time({"COMPRESSION_TIME":"2.5","DATA_RANGE_TIME":""}),2.5)


if __name__=="__main__":
    unittest.main()
