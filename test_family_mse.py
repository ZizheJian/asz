import array,csv,hashlib,json,math,os,random,subprocess,sys,tempfile,unittest
from pathlib import Path

from analyze_family_mse import analyze,save_analysis


def observations(name="field",cubic_mse=1.0,quintic_mse=0.98):
    rows=[]
    for bound,rate,quality in ((0.1,1,40),(0.01,2,60),(0.001,4,80)):
        for family,factor in (("adaptive_4r",1),("fixed_6r",0.9)):
            rows.append({"DATASET":name,"DATA_PATH":f"/synthetic/{name}.f32","REL_EB":bound,"FAMILY":family,"BR":rate*factor,"PSNR":quality,"CUBIC_MSE":cubic_mse,"QUINTIC_MSE":quintic_mse,"PLAN_HASH":f"plan-{bound}","SETTINGS_HASH":f"settings-{bound}"})
    return rows


class FamilyMseTests(unittest.TestCase):
    def test_two_percent_improvement_has_no_runtime_margin(self):
        cases,_,summary=analyze(observations())
        self.assertEqual(summary["mean_pair_tau"],1)
        self.assertEqual(summary["ranking_accuracy"],1)
        self.assertTrue(all(case["mse_choice"]=="fixed_6r" for case in cases))

    def test_disagreement_and_score_regret(self):
        cases,_,summary=analyze(observations(cubic_mse=0.5,quintic_mse=1))
        self.assertEqual(summary["mean_pair_tau"],-1)
        self.assertEqual(summary["ranking_accuracy"],0)
        self.assertTrue(all(case["score_regret"]>0 for case in cases))

    def test_pooling_uses_only_within_case_pairs(self):
        _,files,summary=analyze(observations("small",1e-28,0.98e-28)+observations("large",1e10,2e10))
        self.assertEqual(len(files),2)
        self.assertEqual(summary["comparable_cases"],6)
        self.assertEqual(summary["mean_pair_tau"],0)
        self.assertEqual(summary["ranking_accuracy"],0.5)

    def test_mse_ties_are_not_assigned_tau(self):
        cases,_,summary=analyze(observations(cubic_mse=0,quintic_mse=0))
        self.assertEqual(summary["mse_ties"],3)
        self.assertIsNone(summary["mean_pair_tau"])
        self.assertTrue(all(case["pair_tau"] is None for case in cases))

    def test_rd_ties_are_reported(self):
        rows=observations()
        for row in rows:
            if row["FAMILY"]=="fixed_6r":
                row["BR"]/=0.9
        _,_,summary=analyze(rows)
        self.assertEqual(summary["rd_ties"],3)
        self.assertEqual(summary["comparable_cases"],0)

    def test_common_slope_matches_normalized_rd_formula(self):
        cases,_,_=analyze(observations())
        for case in cases:
            slope=case["slope"]
            self.assertAlmostEqual(case["four_score"],(case["four_psnr"]-slope*case["four_br"])/math.hypot(1,slope))
            self.assertAlmostEqual(case["six_score"],(case["six_psnr"]-slope*case["six_br"])/math.hypot(1,slope))
        self.assertEqual(cases[0]["slope_left_eb"],0.1)
        self.assertEqual(cases[-1]["slope_right_eb"],0.001)

    def test_vertical_tangent_uses_negative_rate(self):
        rows=observations()
        for row in rows:
            row["BR"]=1 if row["FAMILY"]=="adaptive_4r" else 0.9
        cases,_,summary=analyze(rows)
        self.assertEqual(summary["mean_pair_tau"],1)
        self.assertTrue(all(case["slope_kind"]=="vertical" for case in cases))
        self.assertAlmostEqual(cases[0]["four_score"],-1)

    def test_undefined_and_nonmonotone_reference_are_excluded(self):
        for mode in ("degenerate","nonmonotone"):
            rows=observations()
            for row in rows:
                row["BR"]=1 if mode=="degenerate" else 1/row["BR"]
                if mode=="degenerate":
                    row["PSNR"]=40
            _,_,summary=analyze(rows)
            self.assertEqual(summary["excluded_cases"],3)
            self.assertIsNone(summary["mean_pair_tau"])

    def test_nonfinite_mse_is_not_counted_as_agreement(self):
        rows=observations(cubic_mse=math.nan)
        _,_,summary=analyze(rows)
        self.assertEqual(summary["excluded_cases"],3)
        self.assertIsNone(summary["ranking_accuracy"])

    def test_missing_or_duplicate_family_is_rejected(self):
        rows=observations()
        with self.assertRaisesRegex(ValueError,"missing paired family"):
            analyze(rows[:-1])
        with self.assertRaisesRegex(ValueError,"duplicate family"):
            analyze(rows+[rows[0]])

    def test_mismatched_controls_are_rejected(self):
        for control in ("PLAN_HASH","SETTINGS_HASH"):
            rows=observations()
            rows[1][control]="different"
            with self.assertRaisesRegex(ValueError,control):
                analyze(rows)

    def test_unverified_historical_audit_requires_explicit_flag(self):
        rows=observations()
        for row in rows:
            row.pop("PLAN_HASH")
            row.pop("SETTINGS_HASH")
        with self.assertRaisesRegex(ValueError,"unverified"):
            analyze(rows)
        _,_,summary=analyze(rows,allow_unverified_plans=True)
        self.assertEqual(summary["verified_cases"],0)

    def test_report_has_no_nonstandard_json_or_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="asz-mse-analysis-test-") as directory:
            output=Path(directory)/"analysis"
            save_analysis(observations(cubic_mse=math.nan),output)
            report=json.loads((output/"report.json").read_text(),parse_constant=lambda token:self.fail(token))
            self.assertIsNone(report["pooled"]["mean_pair_tau"])
            with self.assertRaises(FileExistsError):
                save_analysis(observations(),output)


@unittest.skipUnless(os.environ.get("ASZ_FAMILY_MSE_EXECUTABLES"),"set ASZ_FAMILY_MSE_EXECUTABLES for the full-compressor smoke test")
class FamilyMseIntegrationTests(unittest.TestCase):
    def test_paired_full_compression_preserves_inputs_and_controls(self):
        with tempfile.TemporaryDirectory(prefix="asz-mse-full-test-") as directory:
            root=Path(directory)
            original=root/"input.f32"
            generator=random.Random(0)
            with original.open("wb") as output:
                array.array("f",(math.sin(i/5)+math.cos(j/6)+k/100+generator.gauss(0,0.001) for i in range(24) for j in range(24) for k in range(24))).tofile(output)
            before=hashlib.sha256(original.read_bytes()).digest()
            manifest=root/"manifest.json"
            manifest.write_text(json.dumps([{"name":"synthetic_smoke_only","data_path":str(original),"data_shape":[24,24,24],"rel_eb_list":[0.01,0.001,0.0001],"asz_parameters":{"max_layer_num":6}}]))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name("run_family_mse_validation.py")),"--manifest",str(manifest),"--executables",os.environ["ASZ_FAMILY_MSE_EXECUTABLES"],"--output",str(root/"result")],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with (root/"result/raw.csv").open(newline="") as source:
                rows=list(csv.DictReader(source))
            self.assertEqual(len(rows),6)
            self.assertEqual({row["FAMILY"] for row in rows},{"adaptive_4r","fixed_6r"})
            for row in rows:
                self.assertEqual(row["STENCIL"],"1D4R" if row["FAMILY"]=="adaptive_4r" else "1D6R")
                self.assertAlmostEqual(float(row["CR"])*float(row["BR"]),32)
            report=json.loads((root/"result/analysis/report.json").read_text())
            self.assertEqual(report["pooled"]["total_cases"],3)
            self.assertEqual(report["pooled"]["verified_cases"],3)
            self.assertEqual(hashlib.sha256(original.read_bytes()).digest(),before)
            self.assertEqual(list((root/"result").rglob("*.asz")),[])


if __name__=="__main__":
    unittest.main()
