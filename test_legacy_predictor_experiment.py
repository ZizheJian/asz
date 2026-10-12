import array,csv,hashlib,json,math,os,random,subprocess,tempfile,unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch


def read_rows(path):
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def run_binary(binary,*arguments):
    return subprocess.run([str(binary),*(str(item) for item in arguments)],capture_output=True,text=True,timeout=60)


class LegacyPredictorExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("ASZ_LEGACY_SWEEP") or not os.environ.get("ASZ_LEGACY_CONCLUDE"):
            raise unittest.SkipTest("set ASZ_LEGACY_SWEEP and ASZ_LEGACY_CONCLUDE to the compiled binaries")
        cls.sweep=Path(os.environ["ASZ_LEGACY_SWEEP"])
        cls.conclude=Path(os.environ["ASZ_LEGACY_CONCLUDE"])
        cls.directory=tempfile.TemporaryDirectory(prefix="asz-legacy-test-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root=Path(cls.directory.name)
        cls.input_path=cls.root/"input.f32"
        generator=random.Random(20261010)
        with cls.input_path.open("wb") as output:
            array.array("f",(generator.uniform(-1,1) for _ in range(14**3))).tofile(output)
        cls.prefix=cls.root/"tiny"
        result=run_binary(cls.sweep,cls.input_path,14,14,14,cls.prefix,"all","0.01,0.001,0.0001")
        if result.returncode:
            raise RuntimeError(result.stderr+result.stdout[-2000:])
        cls.summaries={}
        for family in ("1d4r","2d4r","1d6r"):
            path=cls.root/f"{family}-best.csv"
            result=run_binary(cls.conclude,cls.prefix,family,path)
            if result.returncode:
                raise RuntimeError(result.stderr+result.stdout[-2000:])
            cls.summaries[family]=path
        cls.shared_prefix=cls.root/"shared"
        cls.shared_summaries={}
        for family in ("1d4r","1d6r"):
            result=run_binary(cls.sweep,cls.input_path,14,14,14,cls.shared_prefix,family,"0.01,0.001","transition","shared1d")
            if result.returncode:
                raise RuntimeError(result.stderr+result.stdout[-2000:])
            path=cls.root/f"shared-{family}-best.csv"
            result=run_binary(cls.conclude,cls.shared_prefix,family,path)
            if result.returncode:
                raise RuntimeError(result.stderr+result.stdout[-2000:])
            cls.shared_summaries[family]=path

    def stencils(self,family):
        return [family+suffix for suffix in (("01","02","12") if family=="2d4r" else ("0","1","2"))]

    def test_grid_and_traversal_invariants(self):
        for family,count in (("1d4r",13),("2d4r",13),("1d6r",40)):
            for stencil in self.stencils(family):
                baseline=None
                for order in ("xx0","xx1","xx2"):
                    rows=read_rows(self.root/f"tiny_{stencil}_{order}.csv")
                    self.assertEqual(len(rows),3*count)
                    records={tuple(float(row[key]) for key in (("rel_eb","t1","t2") if family=="1d6r" else ("rel_eb","t1"))):row for row in rows}
                    self.assertEqual(len(records),len(rows))
                    if baseline is not None:
                        self.assertEqual(records.keys(),baseline.keys())
                        for key,row in records.items():
                            for metric in ("SAMPLES","H1","RMSE","MAE","PSNR"):
                                self.assertTrue(math.isclose(float(row[metric]),float(baseline[key][metric]),rel_tol=1e-11,abs_tol=1e-11),(stencil,order,key,metric))
                    baseline=records

    def test_two_stage_score_matches_independent_calculation(self):
        orders=("xx0","xx1","xx2")
        cases=[(self.prefix,family,path) for family,path in self.summaries.items()]+[(self.shared_prefix,family,path) for family,path in self.shared_summaries.items()]
        for prefix,family,path in cases:
            summary={float(row["rel_eb"]):row for row in read_rows(path)}
            bounds=sorted(summary,reverse=True)
            for stencil in self.stencils(family):
                rows={order:read_rows(self.root/f"{prefix.name}_{stencil}_{order}.csv") for order in orders}
                parameter_keys=("t1","t2") if family=="1d6r" else ("t1",)
                groups={(order,bound):sorted((row for row in rows[order] if float(row["rel_eb"])==bound),key=lambda row:tuple(float(row[key]) for key in parameter_keys),reverse=True) for order in orders for bound in bounds}
                averages={(order,bound):tuple(sum(float(row[metric]) for row in groups[order,bound])/len(groups[order,bound]) for metric in ("BR","PSNR")) for order in orders for bound in bounds}
                slopes={}
                chosen={}
                for index,bound in enumerate(bounds):
                    left,right=bounds[max(0,index-1)],bounds[min(len(bounds)-1,index+1)]
                    for order in orders:
                        lo,hi=averages[order,left],averages[order,right]
                        slope=(hi[1]-lo[1])/(hi[0]-lo[0])
                        slopes[order,bound]=slope
                        chosen[order,bound]=max(groups[order,bound],key=lambda row:float(row["PSNR"])-slope*float(row["BR"]))
                second_averages={bound:tuple(sum(float(chosen[order,bound][metric]) for order in orders)/len(orders) for metric in ("BR","PSNR")) for bound in bounds}
                for index,bound in enumerate(bounds):
                    left,right=bounds[max(0,index-1)],bounds[min(len(bounds)-1,index+1)]
                    lo,hi=second_averages[left],second_averages[right]
                    slope=(hi[1]-lo[1])/(hi[0]-lo[0])
                    order=max(orders,key=lambda value:float(chosen[value,bound]["PSNR"])-slope*float(chosen[value,bound]["BR"]))
                    expected=chosen[order,bound]
                    actual=summary[bound]
                    self.assertEqual(actual[stencil+"_traversal_order"],order)
                    for metric in ("BR","PSNR",*parameter_keys):
                        self.assertAlmostEqual(float(actual[stencil+"_"+metric]),float(expected[metric]),places=10)
                    self.assertAlmostEqual(float(actual[stencil+"_coefficient_slope"]),slopes[order,bound],places=8)
                    self.assertAlmostEqual(float(actual[stencil+"_traversal_slope"]),slope,places=8)
                    expected_score=(float(expected["PSNR"])-slope*float(expected["BR"]))/math.sqrt(1+slope*slope)
                    self.assertAlmostEqual(float(actual[stencil+"_score"]),expected_score,places=10)

    def test_existing_outputs_are_preserved(self):
        source=self.root/"tiny_1d4r0_xx0.csv"
        before=hashlib.sha256(source.read_bytes()).digest()
        result=run_binary(self.sweep,self.input_path,14,14,14,self.prefix,"1d4r")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("already exists",result.stderr)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),before)
        summary=self.summaries["1d4r"]
        before=hashlib.sha256(summary.read_bytes()).digest()
        result=run_binary(self.conclude,self.prefix,"1d4r",summary)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(hashlib.sha256(summary.read_bytes()).digest(),before)

    def test_augmented_six_grid_contains_exact_quintic_and_all_four_candidates(self):
        prefix=self.root/"augmented"
        result=run_binary(self.sweep,self.input_path,14,14,14,prefix,"1d6r","0.01,0.001","augmented")
        self.assertEqual(result.returncode,0,result.stderr)
        for stencil in self.stencils("1d6r"):
            rows=read_rows(self.root/f"augmented_{stencil}_xx0.csv")
            self.assertEqual(len(rows),2*52)
            grid={(float(row["t1"]),float(row["t2"])) for row in rows}
            exact=[(119/768,203/768),*((1/6,i/32-1/12) for i in range(13))]
            for point in exact:
                self.assertTrue(any(all(math.isclose(a,b,rel_tol=0,abs_tol=1e-13) for a,b in zip(point,candidate)) for candidate in grid),point)
        selected=self.root/"augmented-best.csv"
        result=run_binary(self.conclude,prefix,"1d6r",selected)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_transition_grid_has_all_anchors_and_midpoints(self):
        equal=(Fraction(0),Fraction(0))
        quintic=(Fraction(119,768),Fraction(203,768))
        four=[(Fraction(1,6),Fraction(k,32)-Fraction(1,12)) for k in range(13)]
        pairs=[(equal,quintic),*((equal,point) for point in four),*((quintic,point) for point in four)]
        expected={equal,quintic,*four,*(tuple((a+b)/2 for a,b in zip(left,right)) for left,right in pairs)}
        self.assertEqual(len(expected),42)
        from run_legacy_predictor_families import six_grid_metadata
        provenance=six_grid_metadata("transition")
        self.assertEqual(provenance["candidate_count"],42)
        self.assertEqual({tuple(Fraction(value) for value in point) for point in provenance["parameters"]},expected)
        for stencil in self.stencils("1d6r"):
            baseline=None
            for order in ("xx0","xx1","xx2"):
                rows=read_rows(self.root/f"shared_{stencil}_{order}.csv")
                self.assertEqual(len(rows),2*42)
                records={tuple(float(row[key]) for key in ("rel_eb","t1","t2")):row for row in rows}
                self.assertEqual(len(records),len(rows))
                grid={key[1:] for key in records}
                self.assertEqual(len(grid),42)
                for point in expected:
                    self.assertTrue(any(all(math.isclose(float(a),b,rel_tol=0,abs_tol=1e-13) for a,b in zip(point,candidate)) for candidate in grid),point)
                if baseline is not None:
                    self.assertEqual(records.keys(),baseline.keys())
                    for key,row in records.items():
                        for metric in ("SAMPLES","H1","RMSE","MAE","PSNR"):
                            self.assertTrue(math.isclose(float(row[metric]),float(baseline[key][metric]),rel_tol=1e-11,abs_tol=1e-11),(stencil,order,key,metric))
                baseline=records

    def test_shared_targets_reproduce_embedded_four_reference_results(self):
        for axis in range(3):
            for order in ("xx0","xx1","xx2"):
                four=read_rows(self.root/f"shared_1d4r{axis}_{order}.csv")
                six=read_rows(self.root/f"shared_1d6r{axis}_{order}.csv")
                embedded={(float(row["rel_eb"]),round(float(row["t2"])+1/12,12)):row for row in six if math.isclose(float(row["t1"]),1/6,rel_tol=0,abs_tol=1e-13)}
                self.assertEqual(len(embedded),len(four))
                for row in four:
                    other=embedded[float(row["rel_eb"]),round(float(row["t1"]),12)]
                    self.assertEqual(int(row["SAMPLES"]),2*14**2)
                    for metric in ("SAMPLES","BR","H1","RMSE","MAE","PSNR"):
                        self.assertTrue(math.isclose(float(row[metric]),float(other[metric]),rel_tol=1e-11,abs_tol=1e-11),(axis,order,row["t1"],metric,row[metric],other[metric]))

    def test_dataset_selection_preserves_the_first_comparison(self):
        from run_legacy_predictor_families import default_datasets,metadata
        self.assertEqual(default_datasets,("isabel","cldice","aramco"))
        with patch.dict("run_legacy_predictor_families.datasets",{"cesmt":("CESM T t31",self.input_path,(14,14,14))}):
            provenance=metadata(("1d4r","1d6r"),"transition","shared1d",("cesmt",))
        self.assertEqual(tuple(provenance["datasets"]),("cesmt",))
        self.assertEqual(provenance["datasets"]["cesmt"]["label"],"CESM T t31")
        self.assertEqual(provenance["target_mode"],"shared1d")
        self.assertEqual(provenance["coefficient_grids"]["1d6r"]["candidate_count"],42)
        from run_legacy_predictor_families import datasets
        self.assertEqual(datasets["cldice"][1].parent.name,"31")
        self.assertEqual(datasets["letkf"][2],(98,1200,1200))
        self.assertEqual(datasets["letkf_qv"][2],(98,1200,1200))
        with patch.dict("run_legacy_predictor_families.datasets",{key:(datasets[key][0],self.input_path,(14,14,14)) for key in ("cldice","letkf","letkf_qv")}):
            provenance=metadata(("1d4r","1d6r"),"transition","shared1d",("cldice","letkf","letkf_qv"))
        self.assertEqual(tuple(provenance["datasets"]),("cldice","letkf","letkf_qv"))

    def test_default_bounds_match_formal_and_validation_configs(self):
        from run_legacy_predictor_families import bounds,project_root
        expected=[0.1,0.01,0.001,0.0001,0.00001]
        self.assertEqual([float(value) for value in bounds.split(",")],expected)
        for name in ("family_mse_validation.json","final_eighteen_asz_refresh_small.json"):
            for case in json.loads((project_root/"configs"/name).read_text()):
                self.assertEqual(case["rel_eb_list"],expected)

    def test_reuse_preserves_raw_data_and_reselects_complete_new_range(self):
        from run_legacy_predictor_families import bounds,metadata,merge_bound_sweeps,raw_paths,reuse_plan
        old=self.root/"reuse-old"
        fresh=self.root/"reuse-fresh"
        merged=self.root/"reuse-merged"
        for directory in (old,fresh,merged):
            directory.mkdir()
        with patch.dict("run_legacy_predictor_families.datasets",{"isabel":("Isabel Pf24",self.input_path,(14,14,14))}):
            provenance=metadata(selected_datasets=("isabel",))
        previous=json.loads(json.dumps(provenance))
        previous["error_bounds"]="0.01,0.001,0.0001,0.000001"
        (old/"provenance.json").write_text(json.dumps(previous))
        for family in ("1d4r","2d4r"):
            for source,destination in zip(raw_paths(self.prefix,family),raw_paths(old/"isabel",family)):
                rows=read_rows(source)
                excluded=[{**row,"rel_eb":"0.000001"} for row in rows if float(row["rel_eb"])==0.0001]
                with destination.open("w",newline="") as output:
                    writer=csv.DictWriter(output,fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows([*rows,*excluded])
        plan=reuse_plan(old,provenance,("1d4r","2d4r"),("isabel",))
        self.assertEqual(plan["computed_bounds"],[0.1,0.00001])
        self.assertEqual(plan["reused_bounds"],[0.01,0.001,0.0001])
        for family in ("1d4r","2d4r"):
            result=run_binary(self.sweep,self.input_path,14,14,14,fresh/"isabel",family,"0.1,0.00001")
            self.assertEqual(result.returncode,0,result.stderr)
            merge_bound_sweeps(old/"isabel",fresh/"isabel",merged/"isabel",family,plan)
            for source,destination in zip(raw_paths(old/"isabel",family),raw_paths(merged/"isabel",family)):
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),plan["raw_sha256"][source.name])
                rows=read_rows(destination)
                self.assertEqual(len(rows),5*13)
                self.assertEqual({float(row["rel_eb"]) for row in rows},{float(value) for value in bounds.split(",")})
                original={(row["rel_eb"],row["t1"]):row for row in read_rows(source)}
                for row in rows:
                    if float(row["rel_eb"]) in plan["reused_bounds"]:
                        self.assertEqual(row,original[row["rel_eb"],row["t1"]])
            result=run_binary(self.conclude,merged/"isabel",family,merged/f"{family}-best.csv")
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(read_rows(merged/f"{family}-best.csv")),5)
        damaged=json.loads(json.dumps(provenance))
        damaged["datasets"]["isabel"]["mtime_ns"]+=1
        with self.assertRaisesRegex(ValueError,"dataset mismatch"):
            reuse_plan(old,damaged,("1d4r","2d4r"),("isabel",))
        duplicate=raw_paths(old/"isabel","1d4r")[0]
        with duplicate.open("a") as output:
            output.write(duplicate.read_text().splitlines()[1]+"\n")
        with self.assertRaisesRegex(ValueError,"duplicate coefficient grid"):
            reuse_plan(old,provenance,("1d4r","2d4r"),("isabel",))

    def test_degenerate_slope_is_rejected(self):
        prefix=self.root/"degenerate"
        for stencil in self.stencils("1d4r"):
            for order in ("xx0","xx1","xx2"):
                with (self.root/f"degenerate_{stencil}_{order}.csv").open("w",newline="") as output:
                    writer=csv.writer(output)
                    writer.writerow(("rel_eb","t1","BR","PSNR"))
                    writer.writerows(((0.01,0,1,40),(0.01,0.25,3,50),(0.001,0,1,60),(0.001,0.25,3,70)))
        result=run_binary(self.conclude,prefix,"1d4r")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("zero bitrate span",result.stderr)
        self.assertFalse((self.root/"degenerate_1d4r_each_sp_best.csv").exists())

    def test_zero_coefficient_span_with_equal_rates_uses_psnr(self):
        prefix=self.root/"equal-coefficient-rate"
        for stencil in self.stencils("1d4r"):
            for order_index,order in enumerate(("xx0","xx1","xx2")):
                with (self.root/f"equal-coefficient-rate_{stencil}_{order}.csv").open("w",newline="") as output:
                    writer=csv.writer(output)
                    writer.writerow(("rel_eb","t1","BR","PSNR"))
                    for bound,quality in ((0.01,40),(0.001,60)):
                        writer.writerows(((bound,0,2,quality+order_index),(bound,0.25,2,quality+5+order_index)))
        summary=self.root/"equal-coefficient-rate-best.csv"
        result=run_binary(self.conclude,prefix,"1d4r",summary)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("equal-rate coefficient candidates",result.stderr)
        for row in read_rows(summary):
            for stencil in self.stencils("1d4r"):
                self.assertEqual(float(row[stencil+"_t1"]),0.25)
                self.assertEqual(row[stencil+"_traversal_order"],"xx2")
                self.assertTrue(math.isnan(float(row[stencil+"_coefficient_slope"])))
                self.assertEqual(row[stencil+"_coefficient_score_kind"],"equal_rate_psnr")
                self.assertEqual(float(row[stencil+"_PSNR"]),47 if float(row["rel_eb"])==0.01 else 67)

    def test_repeated_rd_points_with_equal_rates_are_ranked_by_psnr(self):
        prefix=self.root/"equal-rate"
        for stencil in self.stencils("1d4r"):
            for order_index,order in enumerate(("xx0","xx1","xx2")):
                with (self.root/f"equal-rate_{stencil}_{order}.csv").open("w",newline="") as output:
                    writer=csv.writer(output)
                    writer.writerow(("rel_eb","t1","BR","PSNR"))
                    for bound,good_rate,bad_rate,bad_quality in ((0.1,1,2,40),(0.01,1,3,50),(0.001,2,4,70)):
                        quality=60 if bound>=0.01 else 80
                        writer.writerows(((bound,0.25,good_rate,quality+order_index),(bound,0,bad_rate,bad_quality+order_index)))
        summary=self.root/"equal-rate-best.csv"
        result=run_binary(self.conclude,prefix,"1d4r",summary)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("rank by PSNR (slope undefined)",result.stderr)
        row=next(row for row in read_rows(summary) if float(row["rel_eb"])==0.1)
        for stencil in self.stencils("1d4r"):
            self.assertEqual(row[stencil+"_traversal_order"],"xx2")
            self.assertEqual(float(row[stencil+"_PSNR"]),62)
            self.assertEqual(float(row[stencil+"_score"]),62)
            self.assertTrue(math.isnan(float(row[stencil+"_traversal_slope"])))
            self.assertEqual(row[stencil+"_traversal_score_kind"],"equal_rate_psnr")

    def test_zero_span_with_unequal_candidate_rates_is_still_rejected(self):
        prefix=self.root/"unequal-rate"
        for stencil in self.stencils("1d4r"):
            for order_index,order in enumerate(("xx0","xx1","xx2")):
                with (self.root/f"unequal-rate_{stencil}_{order}.csv").open("w",newline="") as output:
                    writer=csv.writer(output)
                    writer.writerow(("rel_eb","t1","BR","PSNR"))
                    for bound,good_rate,bad_rate,bad_quality in ((0.1,1,2,40),(0.01,1,3,50),(0.001,2,4,70)):
                        quality=60 if bound>=0.01 else 80
                        writer.writerows(((bound,0.25,good_rate+order_index/10,quality),(bound,0,bad_rate+order_index/10,bad_quality)))
        result=run_binary(self.conclude,prefix,"1d4r")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("zero bitrate span in traversal-selection slope",result.stderr)


if __name__=="__main__":
    unittest.main()
