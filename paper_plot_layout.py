import math

PANEL_ASPECT=1.618
AXIS_FRAME_WIDTH=.5
TICK_WIDTH=.45
TICK_LENGTH=2
X_TICK_PAD=3
Y_TICK_PAD=1
GRID_COLOR="#9e9e9e"
GRID_WIDTH=.45
GRID_ALPHA=.55


def style_plot_axis(axis,grid_axis="both"):
    axis.tick_params(axis="x",direction="in",top=False,length=TICK_LENGTH,width=TICK_WIDTH,pad=X_TICK_PAD)
    axis.tick_params(axis="y",direction="in",right=False,length=TICK_LENGTH,width=TICK_WIDTH,pad=Y_TICK_PAD)
    axis.grid(True,axis=grid_axis,color=GRID_COLOR,linestyle="--",linewidth=GRID_WIDTH,alpha=GRID_ALPHA)
    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_linewidth(AXIS_FRAME_WIDTH)


def place_legend_above_axes(figure,legend,axes,x=.5,gap_pt=2):
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    transform=figure.transFigure.inverted()
    legend_height=legend.get_window_extent(renderer).transformed(transform).height
    axes_top=max(axis.get_position().y1 for axis in axes if axis.get_visible())
    gap=gap_pt/72/figure.get_size_inches()[1]
    legend.set_bbox_to_anchor((x,axes_top+gap+legend_height),transform=figure.transFigure)


def add_panel_captions(figure,axes,labels,fontsize,gap_pt=2):
    axes=list(axes)
    if len(axes)!=len(labels):
        raise ValueError("axes and labels must have the same length")
    captions=[figure.text(0,0,label,ha="center",va="top",fontsize=fontsize) for label in labels]
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    height=figure.get_size_inches()[1]
    gap=gap_pt/72/height
    for axis,caption in zip(axes,captions):
        boxes=[label.get_window_extent(renderer) for label in axis.get_xticklabels() if label.get_visible()]
        if axis.xaxis.label.get_text():
            boxes.append(axis.xaxis.label.get_window_extent(renderer))
        bottom=min(box.y0 for box in boxes)/figure.dpi/height if boxes else axis.get_position().y0
        caption.set_position((sum(axis.get_position().intervalx)/2,bottom-gap))
    return captions


def _visible_tick_bottom(figure,axis,renderer):
    lower,upper=axis.get_xlim()
    boxes=[label.get_window_extent(renderer) for value,label in zip(axis.get_xticks(),axis.get_xticklabels()) if label.get_visible() and min(lower,upper)<=value<=max(lower,upper)]
    if boxes:
        return min(box.y0 for box in boxes)/figure.dpi/figure.get_size_inches()[1]
    return axis.get_position().y0


def add_panel_footers(figure,axes,labels,columns,xlabel,fontsize,caption_gap_pt=1,xlabel_gap_pt=3,xlabel_x=.5):
    axes=list(axes)
    if len(axes)!=len(labels):
        raise ValueError("axes and labels must have the same length")
    captions=[figure.text(0,0,label,ha="center",va="top",fontsize=fontsize) for label in labels]
    shared_xlabel=figure.text(xlabel_x,0,xlabel,ha="center",va="top",fontsize=fontsize)
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    height=figure.get_size_inches()[1]
    caption_gap=caption_gap_pt/72/height
    for axis,caption in zip(axes,captions):
        caption.set_position((sum(axis.get_position().intervalx)/2,_visible_tick_bottom(figure,axis,renderer)-caption_gap))
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    transform=figure.transFigure.inverted()
    rows=math.ceil(len(axes)/columns)
    bottom_captions=captions[(rows-1)*columns:]
    caption_bottom=min(caption.get_window_extent(renderer).transformed(transform).y0 for caption in bottom_captions)
    shared_xlabel.set_y(caption_bottom-xlabel_gap_pt/72/height)
    return captions,shared_xlabel
