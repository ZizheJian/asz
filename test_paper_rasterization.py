import hashlib,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from rasterize_paper_figures import rasterize_pdf


@unittest.skipUnless(shutil.which("pdftoppm"),"pdftoppm is required")
class PaperRasterizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix="asz-raster-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.source=self.root/"source.pdf"
        figure,axis=plt.subplots(figsize=(3.5,1.2))
        axis.plot([0,1],[0,1],color="red")
        axis.set_xlabel("Bit rate",fontsize=8)
        figure.savefig(self.source)
        plt.close(figure)

    def test_final_column_width_rgb_dpi_and_source_preservation(self):
        digest=hashlib.sha256(self.source.read_bytes()).hexdigest()
        target=self.root/"nested"/"figure.png"
        size=rasterize_pdf(self.source,target)
        with Image.open(target) as image:
            self.assertEqual(image.size,size)
            self.assertEqual(image.width,1046)
            self.assertLessEqual(abs(image.height-image.width*1.2/3.5),1)
            self.assertEqual(image.mode,"RGB")
            self.assertEqual(image.getpixel((0,0)),(255,255,255))
            for dpi in image.info["dpi"]:
                self.assertAlmostEqual(dpi,300,places=2)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),digest)
        self.assertEqual(rasterize_pdf(self.source,target),size)

    def test_pixel_width_follows_final_physical_size(self):
        width,_=rasterize_pdf(self.source,self.root/"half.png",width_pt=126,dpi=300)
        self.assertEqual(width,523)

    def test_invalid_dimensions_are_rejected_before_rendering(self):
        with patch("rasterize_paper_figures.subprocess.run") as run:
            for width,dpi in ((0,300),(-1,300),(252,0),(252,-1),(float("nan"),300),(252,float("inf")),(0.01,1)):
                with self.subTest(width=width,dpi=dpi),self.assertRaises(ValueError):
                    rasterize_pdf(self.source,self.root/"invalid.png",width_pt=width,dpi=dpi)
            run.assert_not_called()

    def test_wrong_extensions_and_source_alias_are_rejected(self):
        with self.assertRaises(ValueError):
            rasterize_pdf(self.source,self.source)
        alias=self.root/"alias.png"
        alias.symlink_to(self.source)
        with self.assertRaises(ValueError):
            rasterize_pdf(self.source,alias)


if __name__=="__main__":unittest.main()
