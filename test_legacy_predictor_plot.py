import csv,tempfile,unittest
from pathlib import Path
import numpy as np

from run_legacy_predictor_families import plot


class PredictorPlotTests(unittest.TestCase):
    def write_six_panel_summaries(self,directory,keys):
        directory.mkdir(parents=True,exist_ok=True)
        for key in keys:
            for family in ("1d4r","1d6r"):
                fields=["rel_eb",*(f"{family}{direction}_{metric}" for direction in range(3) for metric in ("BR","PSNR"))]
                with (directory/f"{key}-{family}-best.csv").open("w",newline="") as output:
                    writer=csv.DictWriter(output,fieldnames=fields)
                    writer.writeheader()
                    for index in range(5):
                        row={"rel_eb":10**(-1-index)}
                        for direction in range(3):
                            row[f"{family}{direction}_BR"]=(direction+1)*10**(index-4)/4
                            row[f"{family}{direction}_PSNR"]=45+20*index+direction
                        writer.writerow(row)

    def test_single_column_layout_and_equal_direction_styling(self):
        with tempfile.TemporaryDirectory(prefix="asz-plot-test-") as directory:
            root=Path(directory)
            for selected_families,keys in ((("1d4r","2d4r"),("isabel","cldice","aramco")),(("1d4r","1d6r"),("isabel","cesmt","aramco")),(("1d4r","1d6r"),("cldice","letkf","letkf_qv")),(("1d4r","1d6r"),("aramco","letkf","qmcpack"))):
                with self.subTest(families=selected_families):
                    for key in keys:
                        for family in selected_families:
                            stencils=[family+suffix for suffix in (("01","02","12") if family=="2d4r" else ("0","1","2"))]
                            fields=["rel_eb",*(stencil+"_"+metric for stencil in stencils for metric in ("BR","PSNR"))]
                            with (root/f"{key}-{family}-best.csv").open("w",newline="") as output:
                                writer=csv.DictWriter(output,fieldnames=fields)
                                writer.writeheader()
                                for bound_index in range(5):
                                    row={"rel_eb":10**(-1-bound_index)}
                                    for direction,stencil in enumerate(stencils):
                                        row[stencil+"_BR"]=(direction+1)*10**(bound_index-4)/4
                                        row[stencil+"_PSNR"]=45+20*bound_index+direction
                                    writer.writerow(row)
                    figure=plot(root,selected_families,keys,root/"figures")
                    figure.canvas.draw()
                    renderer=figure.canvas.get_renderer()
                    self.assertEqual(figure.get_size_inches()[0],3.5)
                    self.assertEqual(len(figure.axes),3)
                    label_box=figure._supxlabel.get_window_extent(renderer)
                    pixels=np.asarray(figure.canvas.buffer_rgba())
                    for index,axis in enumerate(figure.axes):
                        self.assertEqual(axis.get_title(),"")
                        self.assertEqual(len(axis.lines),6)
                        patterns=[line._unscaled_dash_pattern for line in axis.lines]
                        self.assertEqual(len(set(patterns)),6)
                        self.assertEqual([pattern[1] for pattern in patterns[:3]],[pattern[1] for pattern in patterns[3:]])
                        for blue,red in zip(axis.lines[:3],axis.lines[3:]):
                            self.assertEqual(blue._unscaled_dash_pattern[0],sum(blue._unscaled_dash_pattern[1])/2)
                            self.assertEqual(red._unscaled_dash_pattern[0],0)
                            np.testing.assert_array_equal(blue.get_xdata(),red.get_xdata())
                            np.testing.assert_array_equal(blue.get_ydata(),red.get_ydata())
                        self.assertEqual(len({line.get_color() for line in axis.lines}),2)
                        for line in axis.lines:
                            self.assertTrue(line.is_dashed())
                            self.assertEqual(line.get_marker(),"None")
                            self.assertEqual(line.get_linewidth(),0.8)
                            self.assertEqual(line.get_dash_capstyle(),"butt")
                            dashes=line._unscaled_dash_pattern[1]
                            self.assertAlmostEqual(sum(dashes[::2])/sum(dashes),0.6)
                            self.assertEqual(len(line.get_xdata()),5)
                        box=axis.get_window_extent(renderer)
                        self.assertAlmostEqual(box.width/box.height,1.618,places=6)
                        tile=pixels[pixels.shape[0]-int(box.y1):pixels.shape[0]-int(box.y0),int(box.x0):int(box.x1),:3].astype(float)
                        self.assertGreater(np.count_nonzero((tile[:,:,2]>1.5*tile[:,:,0])&(tile[:,:,2]>tile[:,:,1])),10)
                        self.assertGreater(np.count_nonzero((tile[:,:,0]>1.5*tile[:,:,2])&(tile[:,:,0]>tile[:,:,1])),10)
                        caption=next(text for text in figure.texts if text.get_gid()==f"panel-caption-{index}")
                        self.assertGreater(caption.get_window_extent(renderer).y0,label_box.y1)
                        self.assertLess(caption.get_window_extent(renderer).y1,axis.get_window_extent(renderer).y0)
                    legend_box=figure.legends[0].get_window_extent(renderer)
                    gap=(legend_box.y0-figure.axes[0].get_window_extent(renderer).y1)*72/figure.dpi
                    self.assertAlmostEqual(gap,2,places=5)
                    x_ticks=[label for axis in figure.axes for value,label in zip(axis.get_xticks(),axis.get_xticklabels()) if axis.get_xlim()[0]<=value<=axis.get_xlim()[1]]
                    captions=[text for text in figure.texts if (text.get_gid() or "").startswith("panel-caption-")]
                    x_gap=(min(text.get_window_extent(renderer).y0 for text in captions)-label_box.y1)*72/figure.dpi
                    self.assertAlmostEqual(x_gap,2,places=5)
                    caption_gap=(min(label.get_window_extent(renderer).y0 for label in x_ticks)-max(text.get_window_extent(renderer).y1 for text in captions))*72/figure.dpi
                    self.assertAlmostEqual(caption_gap,3,places=5)
                    y_gap=(min(label.get_window_extent(renderer).x0 for label in figure.axes[0].get_yticklabels())-figure._supylabel.get_window_extent(renderer).x1)*72/figure.dpi
                    self.assertAlmostEqual(y_gap,2,places=5)
                    texts=[*figure.texts,*(figure.legends[0].get_texts()),*x_ticks,*(label for axis in figure.axes for value,label in zip(axis.get_yticks(),axis.get_yticklabels()) if label.get_visible() and axis.get_ylim()[0]<=value<=axis.get_ylim()[1])]
                    for text in texts:
                        self.assertEqual(text.get_fontsize(),8)
                        box=text.get_window_extent(renderer)
                        self.assertGreaterEqual(box.x0,0)
                        self.assertGreaterEqual(box.y0,0)
                        self.assertLessEqual(box.x1,figure.bbox.width)
                        self.assertLessEqual(box.y1,figure.bbox.height)
                    filename=f"iv-{'-vs-'.join(selected_families)}-legacy-middle"
                    for suffix in ("pdf","png"):
                        self.assertTrue((root/"figures"/f"{filename}.{suffix}").is_file())

    def test_six_panel_layout_with_measured_and_explicitly_pending_datasets(self):
        with tempfile.TemporaryDirectory(prefix="asz-six-panel-test-") as directory:
            root=Path(directory)
            self.write_six_panel_summaries(root,("isabel","cesmt","aramco"))
            keys=("isabel","cesmt","letkf_qv","aramco","cldice","letkf")
            figure=plot(root,("1d4r","1d6r"),keys,root/"figures",allow_missing=True)
            figure.canvas.draw()
            renderer=figure.canvas.get_renderer()
            self.assertEqual(figure.get_size_inches()[0],3.5)
            self.assertEqual(len(figure.axes),6)
            self.assertGreater(figure.axes[0].get_position().y0,figure.axes[3].get_position().y1)
            for index,axis in enumerate(figure.axes):
                box=axis.get_window_extent(renderer)
                self.assertAlmostEqual(box.width/box.height,1.618,places=6)
                self.assertEqual(len(axis.lines),6 if index in (0,1,3) else 0)
                pending=[text for text in axis.texts if text.get_gid()==f"pending-{keys[index]}"]
                self.assertEqual(len(pending),0 if index in (0,1,3) else 1)
                caption=next(text for text in figure.texts if text.get_gid()==f"panel-caption-{index}")
                self.assertTrue(caption.get_text().startswith(f"({chr(97+index)})"))
                self.assertLess(caption.get_window_extent(renderer).y1,axis.get_window_extent(renderer).y0)
                if index<3:
                    self.assertGreater(caption.get_window_extent(renderer).y0,figure.axes[3].get_window_extent(renderer).y1)
                else:
                    self.assertGreater(caption.get_window_extent(renderer).y0,figure._supxlabel.get_window_extent(renderer).y1)
            captions=[next(text for text in figure.texts if text.get_gid()==f"panel-caption-{index}") for index in range(6)]
            self.assertEqual(len({text.get_position()[1] for text in captions[:3]}),1)
            self.assertEqual(len({text.get_position()[1] for text in captions[3:]}),1)
            x_gap=(min(text.get_window_extent(renderer).y0 for text in captions[3:])-figure._supxlabel.get_window_extent(renderer).y1)*72/figure.dpi
            self.assertAlmostEqual(x_gap,2,places=5)
            gap=(figure.legends[0].get_window_extent(renderer).y0-figure.axes[0].get_window_extent(renderer).y1)*72/figure.dpi
            self.assertAlmostEqual(gap,2,places=5)
            for text in [*figure.texts,*figure.legends[0].get_texts(),*(text for axis in figure.axes for text in axis.texts)]:
                self.assertEqual(text.get_fontsize(),8)
                box=text.get_window_extent(renderer)
                self.assertGreaterEqual(box.x0,0)
                self.assertGreaterEqual(box.y0,0)
                self.assertLessEqual(box.x1,figure.bbox.width)
                self.assertLessEqual(box.y1,figure.bbox.height)

    def test_six_panel_plot_combines_completed_summaries_from_two_directories(self):
        with tempfile.TemporaryDirectory(prefix="asz-six-source-test-") as directory:
            root=Path(directory)
            first,second=root/"first",root/"second"
            self.write_six_panel_summaries(first,("isabel","cesmt","aramco"))
            self.write_six_panel_summaries(second,("cldice","letkf","letkf_qv"))
            keys=("isabel","cesmt","letkf_qv","aramco","cldice","letkf")
            figure=plot(first,("1d4r","1d6r"),keys,root/"figures",additional_outputs=(second,))
            self.assertEqual(len(figure.axes),6)
            self.assertTrue(all(len(axis.lines)==6 for axis in figure.axes))
            self.assertFalse(any(axis.texts for axis in figure.axes))

    def test_missing_or_partial_summaries_are_not_silently_plotted(self):
        with tempfile.TemporaryDirectory(prefix="asz-missing-panel-test-") as directory:
            root=Path(directory)
            self.write_six_panel_summaries(root,("isabel",))
            with self.assertRaisesRegex(FileNotFoundError,"missing complete"):
                plot(root,("1d4r","1d6r"),("isabel","cesmt"),root/"figures")
            (root/"isabel-1d6r-best.csv").write_text("rel_eb\n0.1\n")
            with self.assertRaisesRegex(FileNotFoundError,"missing complete"):
                plot(root,("1d4r","1d6r"),("isabel",),root/"figures")


if __name__=="__main__":
    unittest.main()
