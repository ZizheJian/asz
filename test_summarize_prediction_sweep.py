import csv
import tempfile
import unittest
from pathlib import Path

from summarize_prediction_sweep import filter_rows,read_rows,summarize,validate_grid


class PredictionSweepSummaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.directory=Path(self.temporary.name)
        self.prefix=self.directory/"sample"
        header=("rel_eb","t1","BR","H1","PSNR","RMSE","MAE","SAMPLES")
        for axis in range(3):
            for order in range(3):
                path=self.directory/f"sample_1d4r{axis}_xx{order}.csv"
                with open(path,"w",newline="",encoding="utf-8") as output_file:
                    writer=csv.DictWriter(output_file,fieldnames=header,lineterminator="\n")
                    writer.writeheader()
                    for bound,base_rate,base_psnr in ((.1,1,40),(.01,2,50),(.001,3,60)):
                        for coefficient in (.2,.3):
                            penalty=abs(axis-1)+order+abs(coefficient-.3)*10
                            writer.writerow({"rel_eb":bound,"t1":coefficient,"BR":base_rate+penalty*.01,"H1":base_rate+penalty*.02,"PSNR":base_psnr-penalty,"RMSE":penalty+1,"MAE":penalty+2,"SAMPLES":100})

    def tearDown(self):
        self.temporary.cleanup()

    def test_retain_axis_selects_coefficient_and_order(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,("axis",),"br-psnr")
        self.assertEqual(len(selected),9)
        self.assertTrue(all(row["qb_order"]==0 for row in selected))
        self.assertTrue(all(row["coefficient"]=="0.29999999999999999" for row in selected))

    def test_retain_coefficient_with_filters(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        rows=filter_rows(rows,{"0"},{0},())
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,("coefficient",),"h1-psnr")
        self.assertEqual(len(selected),6)
        self.assertEqual({row["axis"] for row in selected},{"0"})
        self.assertEqual({row["qb_order"] for row in selected},{0})

    def test_rmse_criterion(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,(),"rmse")
        self.assertEqual(len(selected),3)
        self.assertTrue(all(row["axis"]=="1" and row["qb_order"]==0 for row in selected))


if __name__=="__main__":
    unittest.main()
