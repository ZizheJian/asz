import math


def layout_rd_panels(figure,panel_axes,legend,labels,columns,aspect=1.618,legend_x=0.5575,label_x=0.5575):
    # 固定绘图区的物理宽高比；文字间距以最终论文中的pt计算。
    rows=math.ceil(len(panel_axes)/columns)
    width=float(figure.get_size_inches()[0])
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    panel_height=panel_axes[0].get_window_extent(renderer).width/figure.dpi/aspect

    def tick_bottom(row_axes):
        boxes=[label.get_window_extent(renderer) for axis in row_axes for value,label in zip(axis.get_xticks(),axis.get_xticklabels()) if label.get_visible() and axis.get_xlim()[0]<=value<=axis.get_xlim()[1]]
        return min((box.y0 for box in boxes),default=min(axis.get_window_extent(renderer).y0 for axis in row_axes)-10*figure.dpi/72)

    row_axes=[panel_axes[row*columns:(row+1)*columns] for row in range(rows)]
    tick_depths=[max(axis.get_window_extent(renderer).y0 for axis in axes)/figure.dpi-tick_bottom(axes)/figure.dpi for axes in row_axes]
    captions=[figure.text(0,0,label,ha="center",va="top",fontsize=8,gid=f"panel-caption-{index}") for index,label in enumerate(labels)]
    xlabel=figure.supxlabel("Bit rate (bits/value)",x=label_x,y=0,va="top",fontsize=8)
    ylabel=figure.supylabel("PSNR (dB)",fontsize=8)
    caption_height=max(text.get_window_extent(renderer).height for text in captions)/figure.dpi
    xlabel_height=xlabel.get_window_extent(renderer).height/figure.dpi
    header=legend.get_window_extent(renderer).height/figure.dpi+4/72
    footer=tick_depths[-1]+3/72+caption_height+2/72+xlabel_height+2/72
    row_gap=max(tick_depths[:-1])+3/72+caption_height+6/72 if rows>1 else 0
    height=header+rows*panel_height+(rows-1)*row_gap+footer
    figure.set_size_inches(width,height,forward=True)
    figure.subplots_adjust(top=1-header/height,bottom=footer/height,hspace=row_gap/panel_height)
    legend.set_bbox_to_anchor((legend_x,1-2/72/height))
    figure.canvas.draw()
    renderer=figure.canvas.get_renderer()
    transform=figure.transFigure.inverted()
    for row,axes in enumerate(row_axes):
        top=tick_bottom(axes)/figure.dpi/height-3/72/height
        for index,axis in enumerate(axes,start=row*columns):
            captions[index].set_position((sum(axis.get_position().intervalx)/2,top))
    caption_bottom=min(text.get_window_extent(renderer).transformed(transform).y0 for text in captions[(rows-1)*columns:])
    xlabel.set_y(caption_bottom-2/72/height)
    tick_left=min(label.get_window_extent(renderer).transformed(transform).x0 for index,axis in enumerate(panel_axes) if index%columns==0 for value,label in zip(axis.get_yticks(),axis.get_yticklabels()) if label.get_visible() and axis.get_ylim()[0]<=value<=axis.get_ylim()[1])
    ylabel_width=ylabel.get_window_extent(renderer).transformed(transform).width
    ylabel.set_x(tick_left-ylabel_width-2/72/width)
    ylabel.set_y((min(axis.get_position().y0 for axis in panel_axes)+max(axis.get_position().y1 for axis in panel_axes))/2)
