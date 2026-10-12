import csv,json,unittest
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import test_1d6r_coefficients
from analyze_1d6r_coefficients import analyze,file_hash
from plot_1d6r_coefficients import load_selected,plot,render


class CoefficientPlotTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_1d6r_coefficients.CoefficientSelectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.directory=self.fixture.root/"analysis"
        analyze([self.fixture.source],self.directory,["test"])
        self.addCleanup(plt.close,"all")

    def rewrite(self,rows):
        with (self.directory/"selected.csv").open("w",newline="") as output:
            writer=csv.DictWriter(output,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_complete_fixed_curves_keep_measured_coordinates(self):
        datasets,_,hashes=load_selected(self.directory)
        dataset=datasets["test"]
        self.assertEqual(len(dataset["curves"]),2)
        figure=render(datasets)
        self.assertEqual(figure.get_size_inches()[0],3.5)
        figure.canvas.draw()
        box=figure.axes[0].get_window_extent(figure.canvas.get_renderer())
        self.assertAlmostEqual(box.width/box.height,1.618,places=6)
        self.assertEqual(len(figure.axes[0].lines),3)
        for parameter,curve in dataset["curves"].items():
            line=next(line for line in figure.axes[0].lines if line.get_gid()==f"coefficient-test-{parameter[0]}-{parameter[1]}")
            self.assertEqual(list(line.get_xdata()),[curve[bound]["BR"] for bound in dataset["bounds"]])
            self.assertEqual(list(line.get_ydata()),[curve[bound]["PSNR"] for bound in dataset["bounds"]])
            self.assertEqual(line.get_marker(),"None")
        self.assertEqual(hashes,{path:file_hash(Path(path)) for path in hashes})

    def test_detail_only_changes_view_not_curve_points(self):
        datasets,_,_=load_selected(self.directory)
        main,detail=render(datasets),render(datasets,True)
        for left,right in zip(main.axes[0].lines,detail.axes[0].lines):
            self.assertEqual(list(left.get_xdata()),list(right.get_xdata()))
            self.assertEqual(list(left.get_ydata()),list(right.get_ydata()))
        self.assertNotEqual(main.axes[0].get_xlim(),detail.axes[0].get_xlim())

    def test_all_other_coefficients_share_one_background_style(self):
        datasets,_,_=load_selected(self.directory)
        dataset=datasets["test"]
        equal=dataset["curves"][(0,0)]
        for parameter,kind in (((1/6,0),"embedded_1d4r"),((1/12,0),"transition")):
            dataset["curves"][parameter]={bound:{**row,"t1":parameter[0],"t2":parameter[1],"coefficient_kind":kind} for bound,row in equal.items()}
        figure=render(datasets)
        lines=figure.axes[0].lines
        backgrounds=lines[:3]
        self.assertEqual(len({(line.get_color(),line.get_linestyle(),line.get_linewidth(),line.get_alpha()) for line in backgrounds}),1)
        self.assertEqual(backgrounds[0].get_color(),"0.72")
        self.assertTrue(all(not line.is_dashed() for line in backgrounds))
        self.assertNotEqual(lines[-2].get_color(),backgrounds[0].get_color())
        self.assertGreater(lines[-2].get_linewidth(),backgrounds[0].get_linewidth())
        self.assertTrue(lines[-1].is_dashed())
        legend=figure.legends[0]
        self.assertEqual([text.get_text() for text in legend.get_texts()],["Fixed quintic","Best per error bound","Other coefficients"])
        gray=legend.get_lines()[-1]
        self.assertEqual((gray.get_color(),gray.get_linestyle(),gray.get_linewidth()),(backgrounds[0].get_color(),backgrounds[0].get_linestyle(),backgrounds[0].get_linewidth()))

    def test_three_measured_panels_have_no_placeholder_and_keep_readable_labels(self):
        datasets,_,_=load_selected(self.directory)
        dataset=datasets["test"]
        datasets={key:{**dataset,"label":label} for key,label in (("aramco","Aramco 1800"),("letkf","LETKF PRES"),("qmcpack","QMCPACK orbital 0"))}
        figure=render(datasets)
        figure.canvas.draw()
        renderer=figure.canvas.get_renderer()
        self.assertEqual(len(figure.axes),3)
        self.assertTrue(all(len(axis.lines)==3 for axis in figure.axes))
        self.assertFalse(any(axis.texts for axis in figure.axes))
        self.assertIn("(c) QMCPACK",[text.get_text() for text in figure.texts])
        for text in [*figure.texts,*figure.legends[0].get_texts()]:
            bounds=text.get_window_extent(renderer).transformed(figure.transFigure.inverted())
            self.assertGreaterEqual(bounds.x0,0)
            self.assertLessEqual(bounds.x1,1)
            self.assertGreaterEqual(bounds.y0,0)
            self.assertLessEqual(bounds.y1,1)
        legend_bounds=figure.legends[0].get_window_extent(renderer).transformed(figure.transFigure.inverted())
        self.assertGreaterEqual(legend_bounds.x0,0)
        self.assertLessEqual(legend_bounds.x1,1)
        self.assertGreater(legend_bounds.y0,max(axis.get_position().y1 for axis in figure.axes))
        figure.set_dpi(400)
        figure.canvas.draw()
        renderer=figure.canvas.get_renderer()
        for text in [*figure.texts,*figure.legends[0].get_texts()]:
            bounds=text.get_window_extent(renderer).transformed(figure.transFigure.inverted())
            self.assertGreaterEqual(bounds.x0,0)
            self.assertLessEqual(bounds.x1,1)
            self.assertGreaterEqual(bounds.y0,0)
            self.assertLessEqual(bounds.y1,1)
        for axis in figure.axes:
            box=axis.get_window_extent(renderer)
            self.assertAlmostEqual(box.width/box.height,1.618,places=6)

    def test_duplicate_incomplete_and_invalid_points_are_rejected(self):
        with (self.directory/"selected.csv").open(newline="") as source:
            rows=list(csv.DictReader(source))
        for invalid in (rows+[rows[0]],rows[:-1],[{**rows[0],"axis":""},*rows[1:]]):
            self.rewrite(invalid)
            with self.assertRaises(ValueError):
                load_selected(self.directory)

    def test_caption_placement_and_text_fit_canvas(self):
        datasets,_,_=load_selected(self.directory)
        for placeholder in (False,True):
            figure=render(datasets,placeholder=placeholder)
            figure.canvas.draw()
            renderer=figure.canvas.get_renderer()
            for text in [*figure.texts,*figure.legends[0].get_texts()]:
                bounds=text.get_window_extent(renderer).transformed(figure.transFigure.inverted())
                self.assertGreaterEqual(bounds.x0,0)
                self.assertLessEqual(bounds.x1,1)
                self.assertGreaterEqual(bounds.y0,0)
                self.assertLessEqual(bounds.y1,1)
                self.assertEqual(text.get_fontsize(),8)
                self.assertEqual(text.get_fontfamily(),["STIXGeneral"])
                if text.get_text().startswith("(a)"):
                    self.assertGreater(bounds.y0,figure._supxlabel.get_window_extent(renderer).transformed(figure.transFigure.inverted()).y1)
                    x_gap=(text.get_window_extent(renderer).y0-figure._supxlabel.get_window_extent(renderer).y1)*72/figure.dpi
                    self.assertAlmostEqual(x_gap,2,places=5)
            if placeholder:
                self.assertEqual(len(figure.axes[-1].lines),0)
                self.assertTrue(any(text.get_gid()=="pending-dataset" for text in figure.axes[-1].texts))

    def test_exports_and_provenance_preserve_analysis_and_raw_inputs(self):
        paths=[*self.fixture.source.iterdir(),*self.directory.iterdir()]
        hashes={path:file_hash(path) for path in paths}
        output=self.fixture.root/"figures"
        report=plot(self.directory,output,paper_placeholder=True)
        self.assertEqual(len(report["products"]),6)
        self.assertEqual(report["datasets"]["test"]["coefficient_curves"],2)
        self.assertEqual(report["font_size_pt"],8)
        self.assertEqual(report["panel_width_height_ratio"],1.618)
        self.assertEqual(report["legend_labels"],["Fixed quintic","Best per error bound","Other coefficients"])
        self.assertTrue(all(Path(path).stat().st_size>1000 for path in report["products"]))
        self.assertEqual(json.loads((output/"plot-report.json").read_text()),report)
        self.assertEqual(hashes,{path:file_hash(path) for path in paths})


if __name__=="__main__":
    unittest.main()
