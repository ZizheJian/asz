import csv
import tempfile
import unittest
from pathlib import Path

from summarize_prediction_sweep import filter_rows,read_rows,shared_rd_scores,six_reference_grids,summarize,summarize_two_stage,validate_exhaustive_grid,validate_grid,validate_uniform_samples


class PredictionSweepSummaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.directory=Path(self.temporary.name)
        self.prefix=self.directory/"sample"
        header=("rel_eb","t","BR","H1","PSNR","RMSE","MAE","SAMPLES")
        for axis in range(3):
            for order in range(3):
                path=self.directory/f"sample_1d4r{axis}_xx{order}.csv"
                with open(path,"w",newline="",encoding="utf-8") as output_file:
                    writer=csv.DictWriter(output_file,fieldnames=header,lineterminator="\n")
                    writer.writeheader()
                    for bound,base_rate,base_psnr in ((.1,1,40),(.01,2,50),(.001,3,60)):
                        for coefficient in (index/32 for index in range(13)):
                            penalty=abs(axis-1)+order+abs(coefficient-.3125)*10
                            writer.writerow({"rel_eb":bound,"t":coefficient,"BR":base_rate+penalty*.01,"H1":base_rate+penalty*.02,"PSNR":base_psnr-penalty,"RMSE":penalty+1,"MAE":penalty+2,"SAMPLES":100})

    def tearDown(self):
        self.temporary.cleanup()

    def test_retain_axis_selects_coefficient_and_order(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,("axis",),"br-psnr")
        self.assertEqual(len(selected),9)
        self.assertTrue(all(row["qb_order"]==0 for row in selected))
        self.assertTrue(all(row["coefficient"]=="0.3125" for row in selected))

    def test_retain_coefficient_with_filters(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        rows=filter_rows(rows,{"0"},{0},())
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,("coefficient",),"h1-psnr")
        self.assertEqual(len(selected),39)
        self.assertEqual({row["axis"] for row in selected},{"0"})
        self.assertEqual({row["qb_order"] for row in selected},{0})

    def test_exhaustive_grid_detects_missing_order(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        validate_exhaustive_grid(rows,{"1d4r"},bounds)
        incomplete=[row for row in rows if not (row["axis"]=="2" and row["qb_order"]==2)]
        with self.assertRaisesRegex(ValueError,"QB orders mismatch"):
            validate_exhaustive_grid(incomplete,{"1d4r"},bounds)

    def test_uniform_samples(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        self.assertEqual(validate_uniform_samples(rows),100)
        rows[0]["SAMPLES"]=99
        with self.assertRaisesRegex(ValueError,"sample counts differ"):
            validate_uniform_samples(rows)

    def test_rmse_criterion(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        selected=summarize(rows,bounds,(),"rmse")
        self.assertEqual(len(selected),3)
        self.assertTrue(all(row["axis"]=="1" and row["qb_order"]==0 for row in selected))

    def test_two_stage_selects_coefficient_then_order(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        selected=summarize_two_stage(rows,bounds,"br-psnr")
        self.assertEqual(len(selected),9)
        self.assertTrue(all(row["qb_order"]==0 for row in selected))
        self.assertTrue(all(row["coefficient"]=="0.3125" for row in selected))

    def test_six_reference_grids_have_expected_sizes(self):
        grids=six_reference_grids()
        self.assertEqual({name:len(grid) for name,grid in grids.items()},{"legacy":40,"augmented":52,"transition":42})
        self.assertTrue(all(len(set(grid))==len(grid) for grid in grids.values()))
        self.assertIn((3/256,-25/256),grids["transition"])
        self.assertIn((0,1/4),grids["transition"])
        self.assertIn((0,-1/8),grids["transition"])

    def test_legacy_six_reference_offsets_are_converted_to_weights(self):
        path=self.directory/"legacy_1d6r0_xx0.csv"
        with open(path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=("rel_eb","t1","t2","BR","H1","PSNR","RMSE","MAE","SAMPLES"),lineterminator="\n")
            writer.writeheader()
            writer.writerow({"rel_eb":.001,"t1":119/768,"t2":203/768,"BR":1,"H1":1,"PSNR":80,"RMSE":1,"MAE":1,"SAMPLES":100})
        rows,_=read_rows(self.directory/"legacy",{"1d6r"})
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]["a"],3/256)
        self.assertAlmostEqual(rows[0]["b"],-25/256)
        self.assertIsNone(rows[0]["t"])

    def test_six_reference_weight_columns_are_read_directly(self):
        path=self.directory/"weights_1d6r0_xx0.csv"
        with open(path,"w",newline="",encoding="utf-8") as output_file:
            writer=csv.DictWriter(output_file,fieldnames=("rel_eb","a","b","BR","H1","PSNR","RMSE","MAE","SAMPLES"),lineterminator="\n")
            writer.writeheader()
            writer.writerow({"rel_eb":.001,"a":3/256,"b":-25/256,"BR":1,"H1":1,"PSNR":80,"RMSE":1,"MAE":1,"SAMPLES":100})
        rows,_=read_rows(self.directory/"weights",{"1d6r"})
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]["a"],3/256)
        self.assertAlmostEqual(rows[0]["b"],-25/256)
        self.assertIsNone(rows[0]["t"])

    def test_shared_slope_uses_averaged_auxiliary_bounds(self):
        rows,_=read_rows(self.prefix,{"1d4r"})
        bounds=validate_grid(rows)
        scores,report=shared_rd_scores(rows,bounds,(.01,),"BR",10)
        self.assertEqual(len(scores),3*3*13)
        entry=report["0.01"]
        self.assertEqual(entry["coarse_eb"],.1)
        self.assertEqual(entry["fine_eb"],.001)
        self.assertAlmostEqual(entry["slope"],10)
        neighboring_scores,neighboring_report=shared_rd_scores(rows,bounds,(.01,),"BR",None)
        self.assertEqual(len(neighboring_scores),len(scores))
        self.assertEqual(neighboring_report["0.01"],entry)


if __name__=="__main__":
    unittest.main()
