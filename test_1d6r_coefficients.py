import csv,itertools,json,math,tempfile,unittest
from pathlib import Path

from analyze_1d6r_coefficients import analyze,file_hash,load_dataset,parameter_key,read_manifest,reference_weights,select_coefficients


class CoefficientSelectionTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix="asz-6r-coeff-test-")
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.source=self.root/"raw"
        self.source.mkdir()
        self.parameters=((0,0),(119/768,203/768))
        self.bounds=(0.1,0.01,0.001)
        self.manifest={"families":["1d4r","1d6r"],"error_bounds":",".join(map(str,self.bounds)),"target_mode":"shared1d","datasets":{"test":{"label":"Test","shape":[14,14,14]}},"coefficient_grids":{"1d6r":{"candidate_count":2,"parameters":[["0","0"],["119/768","203/768"]]}}}
        (self.source/"provenance.json").write_text(json.dumps(self.manifest))
        self.write_fixture()

    def write_fixture(self,transform=None):
        for axis,order in itertools.product(range(3),range(3)):
            path=self.source/f"test_1d6r{axis}_xx{order}.csv"
            rows=[]
            for index,bound in enumerate(self.bounds):
                for coefficient,(t1,t2) in enumerate(self.parameters):
                    rate=2*(index+1)+axis/10+order/30+coefficient/5
                    quality=10*(index+1)+4*(axis==(coefficient+index)%3)+2*(order==(coefficient+index+1)%3)+coefficient/2
                    row={"rel_eb":bound,"t1":t1,"t2":t2,"BR":rate,"PSNR":quality,"SAMPLES":392}
                    if transform is not None:
                        row=transform(row,axis,order,coefficient,index)
                    if row is not None:
                        rows.append(row)
            with path.open("w",newline="") as output:
                writer=csv.DictWriter(output,fieldnames=("rel_eb","t1","t2","BR","PSNR","SAMPLES"))
                writer.writeheader()
                writer.writerows(rows)

    def load(self):
        return load_dataset(self.source,"test",read_manifest(self.source))

    def test_each_coefficient_independently_selects_direction_and_order_at_each_bound(self):
        data,bounds,parameters,_=self.load()
        selected,best=select_coefficients(data,bounds,parameters)
        self.assertEqual(len(selected),6)
        self.assertEqual(len(best),3)
        for row in selected:
            index=self.bounds.index(row["rel_eb"])
            coefficient=next(index for index,pair in enumerate(self.parameters) if parameter_key(pair)==parameter_key((row["t1"],row["t2"])))
            self.assertEqual(row["axis"],"xyz"[(coefficient+index)%3])
            self.assertEqual(row["qb_order"],f"xx{(coefficient+index+1)%3}")
            original=next(candidate for candidate in data[row["rel_eb"],parameter_key((row["t1"],row["t2"]))] if candidate["axis"]==row["axis"] and candidate["qb_order"]==row["qb_order"])
            for metric in ("BR","PSNR","SAMPLES","t1","t2","source_csv"):
                self.assertEqual(row[metric],original[metric])

    def test_shared_reference_and_selection_match_independent_all_combination_score(self):
        data,bounds,parameters,_=self.load()
        selected,best=select_coefficients(data,bounds,parameters)
        averages={bound:tuple(math.fsum(row[metric] for (value,_),rows in data.items() if value==bound for row in rows)/18 for metric in ("BR","PSNR")) for bound in bounds}
        for index,bound in enumerate(bounds):
            left,right=bounds[max(0,index-1)],bounds[min(len(bounds)-1,index+1)]
            slope=(averages[right][1]-averages[left][1])/(averages[right][0]-averages[left][0])
            score=lambda row:(row["PSNR"]-slope*row["BR"])/math.sqrt(1+slope*slope)
            for parameters_key in parameters:
                expected=max(data[bound,parameters_key],key=score)
                actual=next(row for row in selected if row["rel_eb"]==bound and parameter_key((row["t1"],row["t2"]))==parameters_key)
                self.assertEqual((actual["axis"],actual["qb_order"]),(expected["axis"],expected["qb_order"]))
                self.assertAlmostEqual(actual["score"],score(expected),places=12)
                self.assertAlmostEqual(actual["slope"],slope,places=12)
            expected=max((row for (value,_),rows in data.items() if value==bound for row in rows),key=score)
            actual=next(row for row in best if row["rel_eb"]==bound)
            self.assertAlmostEqual(actual["score"],score(expected),places=12)

    def test_equal_rates_use_psnr_without_jitter(self):
        self.write_fixture(lambda row,*_:{**row,"BR":1})
        data,bounds,parameters,_=self.load()
        selected,_=select_coefficients(data,bounds,parameters)
        for row in selected:
            self.assertEqual(row["score_kind"],"equal_rate_psnr")
            self.assertIsNone(row["slope"])
            self.assertEqual(row["BR"],1)
            self.assertEqual(row["score"],max(candidate["PSNR"] for candidate in data[row["rel_eb"],parameter_key((row["t1"],row["t2"]))]))

    def test_vertical_reference_uses_minimum_bitrate_and_psnr_tie_break(self):
        self.write_fixture(lambda row,axis,order,*_:{**row,"BR":1+axis/10,"PSNR":row["PSNR"]+100*order})
        data,bounds,parameters,_=self.load()
        selected,_=select_coefficients(data,bounds,parameters)
        for row in selected:
            self.assertEqual(row["score_kind"],"vertical")
            self.assertEqual((row["axis"],row["qb_order"]),("x","xx2"))
            self.assertEqual(row["score"],-1)

    def test_undefined_unequal_rate_reference_is_rejected(self):
        self.write_fixture(lambda row,axis,*_:{**row,"BR":1+axis/10,"PSNR":50})
        data,bounds,_,_=self.load()
        with self.assertRaisesRegex(ValueError,"undefined RD reference"):
            reference_weights(data,bounds)

    def test_nonmonotone_reference_is_rejected(self):
        self.write_fixture(lambda row,*_:{**row,"PSNR":-row["PSNR"]})
        data,bounds,_,_=self.load()
        with self.assertRaisesRegex(ValueError,"nonmonotone RD reference"):
            reference_weights(data,bounds)

    def test_flat_reference_expansion_is_explicit_and_uses_first_nonflat_neighborhood(self):
        self.write_fixture(lambda row,axis,order,coefficient,index:{**row,"BR":1+axis/10+max(0,index-1),"PSNR":50+coefficient+10*max(0,index-1)})
        data,bounds,parameters,_=self.load()
        with self.assertRaisesRegex(ValueError,"undefined RD reference"):
            reference_weights(data,bounds)
        references=reference_weights(data,bounds,True)
        self.assertTrue(references[0.1]["flat_reference_expanded"])
        self.assertEqual((references[0.1]["slope_left_eb"],references[0.1]["slope_right_eb"]),(0.1,0.001))
        self.assertAlmostEqual(references[0.1]["slope"],10)
        self.assertFalse(references[0.01]["flat_reference_expanded"])
        self.assertFalse(references[0.001]["flat_reference_expanded"])
        selected,_=select_coefficients(data,bounds,parameters,True)
        for row in selected:
            self.assertEqual(row["axis"],"x")
            original=next(candidate for candidate in data[row["rel_eb"],parameter_key((row["t1"],row["t2"]))] if candidate["axis"]==row["axis"] and candidate["qb_order"]==row["qb_order"])
            self.assertEqual((row["BR"],row["PSNR"]),(original["BR"],original["PSNR"]))

    def test_expansion_does_not_change_nondegenerate_or_equal_rate_references(self):
        for transform in (None,lambda row,*_:{**row,"BR":1}):
            self.write_fixture(transform)
            data,bounds,_,_=self.load()
            self.assertEqual(reference_weights(data,bounds),reference_weights(data,bounds,True))

    def test_expansion_still_rejects_fully_flat_and_nonmonotone_references(self):
        for direction in (0,-1):
            self.write_fixture(lambda row,axis,order,coefficient,index:{**row,"BR":3+axis/10+direction*max(0,index-1),"PSNR":50+direction*max(0,index-1)})
            data,bounds,_,_=self.load()
            with self.assertRaisesRegex(ValueError,"undefined RD reference|nonmonotone RD reference"):
                reference_weights(data,bounds,True)

    def test_expanded_reference_provenance_is_written(self):
        self.write_fixture(lambda row,axis,order,coefficient,index:{**row,"BR":1+axis/10+max(0,index-1),"PSNR":50+coefficient+10*max(0,index-1)})
        report=analyze([self.source],self.root/"expanded",["test"],True)
        self.assertEqual(report["expanded_references"],[{"dataset":"test","rel_eb":0.1,"slope_left_eb":0.1,"slope_right_eb":0.001}])

    def test_incomplete_coefficient_grid_is_rejected_even_when_all_files_match(self):
        self.write_fixture(lambda row,axis,order,coefficient,index:row if coefficient==0 else None)
        with self.assertRaisesRegex(ValueError,"incomplete coefficient grid"):
            self.load()

    def test_missing_bound_is_rejected_even_when_all_files_match(self):
        self.write_fixture(lambda row,axis,order,coefficient,index:row if index!=1 else None)
        with self.assertRaisesRegex(ValueError,"incomplete or mismatched"):
            self.load()

    def test_missing_qb_order_is_rejected(self):
        (self.source/"test_1d6r2_xx2.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.load()

    def test_duplicate_observation_is_rejected(self):
        path=self.source/"test_1d6r0_xx0.csv"
        with path.open(newline="") as source:
            rows=list(csv.DictReader(source))
        with path.open("a",newline="") as output:
            csv.DictWriter(output,fieldnames=list(rows[0])).writerow(rows[0])
        with self.assertRaisesRegex(ValueError,"duplicate coefficient"):
            self.load()

    def test_nonfinite_and_invalid_sample_counts_are_rejected(self):
        for metric,value in (("BR",0),("BR",math.nan),("PSNR",math.inf),("SAMPLES",391)):
            with self.subTest(metric=metric,value=value):
                self.write_fixture(lambda row,*_:{**row,metric:value})
                with self.assertRaises(ValueError):
                    self.load()

    def test_outputs_preserve_inputs_and_refuse_overwrite(self):
        paths=list(self.source.iterdir())
        before={path:file_hash(path) for path in paths}
        output=self.root/"analysis"
        report=analyze([self.source],output,["test"])
        self.assertFalse(report["measurements_rerun"])
        self.assertEqual(report["datasets"]["test"]["raw_measurements"],54)
        self.assertEqual(report["datasets"]["test"]["selected_points"],6)
        with (output/"selected.csv").open(newline="") as source:
            rows=list(csv.DictReader(source))
        self.assertEqual(len(rows),6)
        self.assertEqual({row["coefficient_kind"] for row in rows},{"equal_weight","quintic"})
        snapshot={path:file_hash(path) for path in output.iterdir()}
        with self.assertRaisesRegex(ValueError,"output already exists"):
            analyze([self.source],output,["test"])
        self.assertEqual(snapshot,{path:file_hash(path) for path in output.iterdir()})
        self.assertEqual(before,{path:file_hash(path) for path in paths})

    def test_ambiguous_or_duplicate_dataset_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"nonempty and distinct"):
            analyze([self.source],self.root/"bad",["test","test"])
        other=self.root/"another"
        other.mkdir()
        (other/"provenance.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,"exactly one input"):
            analyze([self.source,other],self.root/"bad",["test"])


if __name__=="__main__":
    unittest.main()
