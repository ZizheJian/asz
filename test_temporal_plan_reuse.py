import math,unittest

from analyze_temporal_plan_reuse import aggregate_curves,analyze_field,bounds,compression_ratio_loss,interpolate_bit_rate,reuse_windows,transfer_pairs


def curve(psnr_at_target,rate_at_target):
    # 每个误差界相差10倍，PSNR约差20 dB，BR约差3 bits/value
    return {bound:(psnr_at_target+20*math.log10(.001/bound),rate_at_target*2**(3*math.log10(.001/bound))) for bound in bounds}


class TestReuseWindows(unittest.TestCase):
    def test_tail_split_matches_example(self):
        windows=reuse_windows(48,17)
        self.assertEqual([(representative+1,members[0]+1,members[-1]+1) for representative,members in windows],[(16,1,24),(33,25,48)])

    def test_odd_tail_gives_extra_file_to_back(self):
        windows=reuse_windows(48,5)
        self.assertEqual(windows[0],(3,tuple(range(0,6))))
        self.assertEqual(windows[-1],(43,tuple(range(41,48))))
        self.assertEqual(sorted(index for _,members in windows for index in members),list(range(48)))

    def test_single_use_keeps_every_file(self):
        self.assertEqual(reuse_windows(5,1),[(index,(index,)) for index in range(5)])

    def test_rejects_too_short_sequence(self):
        with self.assertRaises(ValueError):
            reuse_windows(16,17)

    def test_transfer_pairs_are_unique(self):
        pairs=transfer_pairs(48)
        self.assertEqual(len(pairs),len(set(pairs)))
        self.assertNotIn((15,15),pairs)
        self.assertIn((15,0),pairs)


class TestLoss(unittest.TestCase):
    def test_aggregate_converts_psnr_to_nmse(self):
        aggregate=aggregate_curves([curve(60,1),curve(80,3)])
        self.assertAlmostEqual(aggregate[.001][0],-10*math.log10((1e-6+1e-8)/2))
        self.assertAlmostEqual(aggregate[.001][1],2)

    def test_interpolation_recovers_measured_point(self):
        self.assertAlmostEqual(interpolate_bit_rate(curve(70,2),70),2)

    def test_interpolation_rejects_outside_target(self):
        with self.assertRaises(ValueError):
            interpolate_bit_rate(curve(70,2),95)

    def test_uniform_rate_increase_gives_expected_loss(self):
        self.assertAlmostEqual(compression_ratio_loss(curve(70,2),curve(70,2.2)),100*(1-1/1.1))

    def test_shifted_psnr_is_matched_before_comparison(self):
        reuse=curve(71,2)
        self.assertLess(compression_ratio_loss(curve(70,2),reuse),0)

    def test_field_summary_uses_aggregate_and_file_range(self):
        count=48
        self_curves=[curve(70+index%3,2) for index in range(count)]
        transfer_curves={(representative,target):curve(70+target%3,2*(1+.01*abs(target-representative))) for representative,target in transfer_pairs(count)}
        summary,detail=analyze_field("isabel_precip",self_curves,transfer_curves)
        self.assertEqual([row["USES"] for row in summary],[1,3,5,9,17])
        self.assertEqual(summary[0]["AGGREGATE_CR_LOSS_PERCENT"],0)
        self.assertAlmostEqual(summary[1]["MIN_FILE_CR_LOSS_PERCENT"],100*(1-1/1.01))
        self.assertAlmostEqual(summary[4]["MAX_FILE_CR_LOSS_PERCENT"],100*(1-1/1.15))
        self.assertTrue(all(row["CR_LOSS_PERCENT"]>0 for row in detail))
        losses=[row["AGGREGATE_CR_LOSS_PERCENT"] for row in summary]
        self.assertEqual(losses,sorted(losses))


if __name__=="__main__":
    unittest.main()
