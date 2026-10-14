import math,unittest

from analyze_predictor_families import coefficient_curves,coefficient_envelope,frontier,matched_rate,best_rate


class PredictorFamilyTests(unittest.TestCase):
    def test_duplicate_rate_keeps_highest_quality(self):
        curve=frontier([{"BR":1,"PSNR":10},{"BR":1,"PSNR":20},{"BR":2,"PSNR":19}])
        self.assertEqual(curve.tolist(),[[1,20]])

    def test_common_quality_does_not_extrapolate(self):
        curve=frontier([{"BR":1,"PSNR":10},{"BR":4,"PSNR":20}])
        self.assertIsNone(matched_rate(curve,9))
        self.assertIsNone(matched_rate(curve,21))
        self.assertAlmostEqual(matched_rate(curve,15),2)

    def test_grid_envelope_contains_fixed_candidate(self):
        rows=[{"BR":1,"PSNR":10,"t":0,"a":0,"b":0},{"BR":4,"PSNR":20,"t":0,"a":0,"b":0},{"BR":2.9,"PSNR":19,"t":1,"a":0,"b":0},{"BR":5,"PSNR":21,"t":1,"a":0,"b":0}]
        curves=coefficient_curves(rows)
        fixed=frontier(rows[:2])
        for quality in (10,12,15,19,20):
            self.assertLessEqual(best_rate(curves,quality),matched_rate(fixed,quality))

    def test_no_candidate_covers_quality(self):
        curve=frontier([{"BR":1,"PSNR":10},{"BR":4,"PSNR":20}])
        self.assertIsNone(best_rate([curve],21))

    def test_higher_quality_candidate_is_not_excluded(self):
        curve=frontier([{"BR":1,"PSNR":30},{"BR":2,"PSNR":40}])
        self.assertEqual(best_rate([curve],20),1)

    def test_envelope_is_monotone_and_not_dominated(self):
        rows=[{"BR":1,"PSNR":30,"t":0,"a":0,"b":0},{"BR":2,"PSNR":40,"t":0,"a":0,"b":0},{"BR":1.5,"PSNR":20,"t":1,"a":0,"b":0},{"BR":2.5,"PSNR":35,"t":1,"a":0,"b":0}]
        envelope=coefficient_envelope(rows)
        for left,right in zip(envelope[:-1],envelope[1:]):
            self.assertLess(left[0],right[0])
            self.assertLess(left[1],right[1])
        self.assertGreaterEqual(envelope[0,1],30)

    def test_nonfinite_quality_is_not_interpolated(self):
        curve=frontier([{"BR":1,"PSNR":10},{"BR":2,"PSNR":math.inf},{"BR":4,"PSNR":20}])
        self.assertEqual(len(curve),2)


if __name__=="__main__":
    unittest.main()
