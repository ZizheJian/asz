import math,subprocess
from pathlib import Path

from PIL import Image


paper_root=Path(__file__).resolve().parent/"新论文"
output_root=paper_root/"revised-fig"/"raster300"
# IEEEtran默认单栏宽21pc=252pt；TeX中1in=72.27pt。
column_width_pt=252
points_per_inch=72.27
figures=(
    "predictor-family-common-final18/iv-1d4r-vs-2d4r-common-targets.pdf",
    "predictor-reference-count-common-final18/iv-1d4r-vs-1d6r-common-targets.pdf",
    "1d6r-coefficients-common-final18/iv-1d6r-coefficients-common-targets.pdf",
)


def rasterize_pdf(source,target,width_pt=column_width_pt,dpi=300):
    source,target=Path(source),Path(target)
    if source.suffix.lower()!=".pdf" or target.suffix.lower()!=".png":
        raise ValueError("rasterization requires a PDF source and a PNG target")
    if source.resolve()==target.resolve():
        raise ValueError("rasterization must not overwrite the source PDF")
    if not math.isfinite(width_pt) or not math.isfinite(dpi) or width_pt<=0 or dpi<=0:
        raise ValueError("figure width and DPI must be finite and positive")
    width=math.floor(width_pt/points_per_inch*dpi)
    if width<1:
        raise ValueError("figure width must cover at least one pixel")
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["pdftoppm","-png","-singlefile","-f","1","-l","1","-scale-to-x",str(width),"-scale-to-y","-1",str(source),str(target.with_suffix(""))],check=True)
    with Image.open(target) as image:
        if image.width!=width:
            raise RuntimeError(f"expected {width} pixels,but rasterizer produced {image.width}")
        size=image.size
        image.convert("RGB").save(target,dpi=(dpi,dpi),optimize=True)
    return size


def main():
    sources=[paper_root/"revised-fig"/name for name in figures]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    for source in sources:
        target=output_root/f"{source.stem}.png"
        width,height=rasterize_pdf(source,target)
        print(f"{target.relative_to(paper_root)}: {width}x{height},effective DPI={width/(column_width_pt/points_per_inch):.2f}")


if __name__=="__main__":main()
