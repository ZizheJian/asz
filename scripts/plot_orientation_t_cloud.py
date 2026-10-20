#!/usr/bin/env python3

# Draw signed-radial local-orientation clouds for one fixed 1D4R axis and one fixed 2D4R axis pair.

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def parse_args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32")
    parser.add_argument("--shape",type=int,nargs=3,default=(449,449,235))
    parser.add_argument("--output-dir",default="results/orientation-t-aramco-20261018")
    parser.add_argument("--block-num",type=int,default=512)
    parser.add_argument("--block-size",type=int,default=8)
    parser.add_argument("--plot-points",type=int,default=60000)
    parser.add_argument("--seed",type=int,default=20261018)
    return parser.parse_args()


def sample_coordinates(shape,block_num,block_size,rng):
    starts=np.column_stack([rng.integers(3,shape[axis]-block_size-2,size=block_num) for axis in range(3)])
    offset=np.indices((block_size,block_size,block_size),dtype=np.int64).reshape(3,-1).T
    coordinates=(starts[:,None,:]+offset[None,:,:]).reshape(-1,3)
    return coordinates


def gather(data,coordinates,axis,offset):
    index=[coordinates[:,0],coordinates[:,1],coordinates[:,2]]
    index[axis]=index[axis]+offset
    return np.asarray(data[tuple(index)],dtype=np.float64)


def ideal_t_1d(data,coordinates,axis):
    center=np.asarray(data[coordinates[:,0],coordinates[:,1],coordinates[:,2]],dtype=np.float64)
    inner=gather(data,coordinates,axis,-1)+gather(data,coordinates,axis,1)
    outer=gather(data,coordinates,axis,-3)+gather(data,coordinates,axis,3)
    slope=inner-outer
    with np.errstate(divide="ignore",invalid="ignore"):
        t=(center-0.25*(inner+outer))/slope
    return t,slope


def ideal_t_2d(data,coordinates,axes):
    center=np.asarray(data[coordinates[:,0],coordinates[:,1],coordinates[:,2]],dtype=np.float64)
    first=gather(data,coordinates,axes[0],-1)+gather(data,coordinates,axes[0],1)
    second=gather(data,coordinates,axes[1],-1)+gather(data,coordinates,axes[1],1)
    slope=first-second
    with np.errstate(divide="ignore",invalid="ignore"):
        t=(center-0.25*(first+second))/slope
    return t,slope


def local_direction(data,coordinates):
    gradient=np.column_stack([0.5*(gather(data,coordinates,axis,1)-gather(data,coordinates,axis,-1)) for axis in range(3)])
    magnitude=np.linalg.norm(gradient,axis=1)
    direction=np.zeros_like(gradient)
    valid=magnitude>0
    direction[valid]=gradient[valid]/magnitude[valid,None]
    flip=(direction[:,2]<0)|((direction[:,2]==0)&(direction[:,1]<0))|((direction[:,2]==0)&(direction[:,1]==0)&(direction[:,0]<0))
    direction[flip]*=-1
    return direction,magnitude


def quantiles(values):
    return {str(probability):float(np.quantile(values,probability)) for probability in (0.1,0.25,0.5,0.75,0.9)}


def style_axis(axis,title,limit):
    axis.set_title(title,pad=8)
    axis.set_xlabel(r"$p_x$",labelpad=-2)
    axis.set_ylabel(r"$p_y$",labelpad=-2)
    axis.set_zlabel(r"$p_z$",labelpad=-2)
    axis.set_xlim(-limit,limit)
    axis.set_ylim(-limit,limit)
    axis.set_zlim(-limit,limit)
    axis.set_box_aspect((1,1,1))
    axis.view_init(elev=22,azim=38)
    axis.grid(False)


def main():
    args=parse_args()
    shape=tuple(args.shape)
    expected_size=int(np.prod(shape))*np.dtype(np.float32).itemsize
    input_path=Path(args.input)
    if input_path.stat().st_size!=expected_size:
        raise RuntimeError("input size does not match the supplied float32 shape")
    output_dir=Path(args.output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(args.seed)
    data=np.memmap(input_path,dtype=np.float32,mode="r",shape=shape)
    coordinates=sample_coordinates(shape,args.block_num,args.block_size,rng)
    direction,gradient_magnitude=local_direction(data,coordinates)
    t_1d_raw,slope_1d=ideal_t_1d(data,coordinates,2)
    t_2d_raw,slope_2d=ideal_t_2d(data,coordinates,(1,2))
    finite=np.isfinite(t_1d_raw)&np.isfinite(t_2d_raw)&np.isfinite(gradient_magnitude)&(gradient_magnitude>0)
    gradient_threshold=float(np.quantile(gradient_magnitude[finite],0.25))
    slope_1d_threshold=float(np.quantile(np.abs(slope_1d[finite]),0.1))
    slope_2d_threshold=float(np.quantile(np.abs(slope_2d[finite]),0.1))
    valid=finite&(gradient_magnitude>=gradient_threshold)&(np.abs(slope_1d)>=slope_1d_threshold)&(np.abs(slope_2d)>=slope_2d_threshold)
    valid_index=np.flatnonzero(valid)
    if valid_index.size==0:
        raise RuntimeError("no valid targets remain after filtering")
    if valid_index.size>args.plot_points:
        valid_index=rng.choice(valid_index,size=args.plot_points,replace=False)
    t_1d=np.clip(t_1d_raw[valid_index],2/32,12/32)
    t_2d=np.clip(t_2d_raw[valid_index],-1/4,1/4)
    selected_direction=direction[valid_index]
    point_1d=t_1d[:,None]*selected_direction
    point_2d=t_2d[:,None]*selected_direction

    figure=plt.figure(figsize=(9.2,4.2),constrained_layout=True)
    axis_1d=figure.add_subplot(1,2,1,projection="3d")
    axis_2d=figure.add_subplot(1,2,2,projection="3d")
    scatter_1d=axis_1d.scatter(point_1d[:,0],point_1d[:,1],point_1d[:,2],c=t_1d,cmap="viridis",vmin=2/32,vmax=12/32,s=1,alpha=0.16,linewidths=0,rasterized=True)
    scatter_2d=axis_2d.scatter(point_2d[:,0],point_2d[:,1],point_2d[:,2],c=t_2d,cmap="coolwarm",vmin=-1/4,vmax=1/4,s=1,alpha=0.16,linewidths=0,rasterized=True)
    style_axis(axis_1d,"1D4R, best axis: z",0.4)
    style_axis(axis_2d,"2D4R, best axis pair: yz",0.4)
    colorbar_1d=figure.colorbar(scatter_1d,ax=axis_1d,fraction=0.045,pad=0.02)
    colorbar_2d=figure.colorbar(scatter_2d,ax=axis_2d,fraction=0.045,pad=0.02)
    colorbar_1d.set_label(r"constrained pointwise $t^*$")
    colorbar_2d.set_label(r"constrained pointwise $t^*$")
    figure.suptitle(r"Aramco signed-radial embedding: $\mathbf{p}_i=t_i^*\mathbf{n}_i$, $n_{i,z}\geq0$",fontsize=10)
    figure.savefig(output_dir/"aramco-orientation-t-cloud.png",dpi=300,bbox_inches="tight",pad_inches=0.08)
    figure.savefig(output_dir/"aramco-orientation-t-cloud.pdf",bbox_inches="tight",pad_inches=0.08)
    plt.close(figure)

    raw_t_1d=t_1d_raw[valid_index]
    raw_t_2d=t_2d_raw[valid_index]
    raw_limit_1d=max(0.4,float(np.quantile(np.abs(raw_t_1d),0.95)))
    raw_limit_2d=max(0.4,float(np.quantile(np.abs(raw_t_2d),0.95)))
    raw_mask_1d=np.abs(raw_t_1d)<=raw_limit_1d
    raw_mask_2d=np.abs(raw_t_2d)<=raw_limit_2d
    raw_point_1d=raw_t_1d[raw_mask_1d,None]*selected_direction[raw_mask_1d]
    raw_point_2d=raw_t_2d[raw_mask_2d,None]*selected_direction[raw_mask_2d]
    raw_figure=plt.figure(figsize=(9.2,4.2),constrained_layout=True)
    raw_axis_1d=raw_figure.add_subplot(1,2,1,projection="3d")
    raw_axis_2d=raw_figure.add_subplot(1,2,2,projection="3d")
    raw_scatter_1d=raw_axis_1d.scatter(raw_point_1d[:,0],raw_point_1d[:,1],raw_point_1d[:,2],c=raw_t_1d[raw_mask_1d],cmap="viridis",vmin=float(np.quantile(raw_t_1d[raw_mask_1d],0.02)),vmax=float(np.quantile(raw_t_1d[raw_mask_1d],0.98)),s=1,alpha=0.16,linewidths=0,rasterized=True)
    raw_scatter_2d=raw_axis_2d.scatter(raw_point_2d[:,0],raw_point_2d[:,1],raw_point_2d[:,2],c=raw_t_2d[raw_mask_2d],cmap="coolwarm",vmin=-raw_limit_2d,vmax=raw_limit_2d,s=1,alpha=0.16,linewidths=0,rasterized=True)
    style_axis(raw_axis_1d,"1D4R, best axis: z",raw_limit_1d)
    style_axis(raw_axis_2d,"2D4R, best axis pair: yz",raw_limit_2d)
    raw_colorbar_1d=raw_figure.colorbar(raw_scatter_1d,ax=raw_axis_1d,fraction=0.045,pad=0.02)
    raw_colorbar_2d=raw_figure.colorbar(raw_scatter_2d,ax=raw_axis_2d,fraction=0.045,pad=0.02)
    raw_colorbar_1d.set_label(r"unconstrained pointwise $t^*$")
    raw_colorbar_2d.set_label(r"unconstrained pointwise $t^*$")
    raw_figure.suptitle(r"Aramco signed-radial embedding: $\mathbf{p}_i=t_i^*\mathbf{n}_i$, central 95% of $|t_i^*|$",fontsize=10)
    raw_figure.savefig(output_dir/"aramco-orientation-t-cloud-raw.png",dpi=300,bbox_inches="tight",pad_inches=0.08)
    raw_figure.savefig(output_dir/"aramco-orientation-t-cloud-raw.pdf",bbox_inches="tight",pad_inches=0.08)
    plt.close(raw_figure)

    selected_direction_yz=selected_direction[:,1:3]
    selected_direction_yz_norm=np.linalg.norm(selected_direction_yz,axis=1)
    selected_direction_yz_valid=selected_direction_yz_norm>1e-12
    selected_direction_yz[selected_direction_yz_valid]/=selected_direction_yz_norm[selected_direction_yz_valid,None]
    raw_mask_1d_yz=raw_mask_1d&selected_direction_yz_valid
    raw_mask_2d_yz=raw_mask_2d&selected_direction_yz_valid
    point_1d_yz=raw_t_1d[raw_mask_1d_yz,None]*selected_direction_yz[raw_mask_1d_yz]
    point_2d_yz=raw_t_2d[raw_mask_2d_yz,None]*selected_direction_yz[raw_mask_2d_yz]
    yz_figure,yz_axes=plt.subplots(1,2,figsize=(8.7,4.15),constrained_layout=True)
    yz_scatter_1d=yz_axes[0].scatter(point_1d_yz[:,0],point_1d_yz[:,1],c=raw_t_1d[raw_mask_1d_yz],cmap="viridis",vmin=float(np.quantile(raw_t_1d[raw_mask_1d_yz],0.02)),vmax=float(np.quantile(raw_t_1d[raw_mask_1d_yz],0.98)),s=1,alpha=0.13,linewidths=0,rasterized=True)
    yz_scatter_2d=yz_axes[1].scatter(point_2d_yz[:,0],point_2d_yz[:,1],c=raw_t_2d[raw_mask_2d_yz],cmap="coolwarm",vmin=-raw_limit_2d,vmax=raw_limit_2d,s=1,alpha=0.13,linewidths=0,rasterized=True)
    for axis,title,limit in zip(yz_axes,("1D4R, best axis: z","2D4R, best axis pair: yz"),(raw_limit_1d,raw_limit_2d)):
        axis.axhline(0,color="0.75",linewidth=0.6)
        axis.axvline(0,color="0.75",linewidth=0.6)
        axis.set_title(title)
        axis.set_xlabel(r"$p_y=t_i^*n_{i,y}$")
        axis.set_ylabel(r"$p_z=t_i^*n_{i,z}$")
        axis.set_xlim(-limit,limit)
        axis.set_ylim(-limit,limit)
        axis.set_aspect("equal")
    yz_colorbar_1d=yz_figure.colorbar(yz_scatter_1d,ax=yz_axes[0],fraction=0.046,pad=0.03)
    yz_colorbar_2d=yz_figure.colorbar(yz_scatter_2d,ax=yz_axes[1],fraction=0.046,pad=0.03)
    yz_colorbar_1d.set_label(r"pointwise analytic $t_i^*$")
    yz_colorbar_2d.set_label(r"pointwise analytic $t_i^*$")
    yz_figure.suptitle(r"Aramco: signed-radial embedding in the $yz$ plane; extreme $|t_i^*|$ omitted")
    yz_figure.savefig(output_dir/"aramco-orientation-t-cloud-yz.png",dpi=300,bbox_inches="tight",pad_inches=0.08)
    yz_figure.savefig(output_dir/"aramco-orientation-t-cloud-yz.pdf",bbox_inches="tight",pad_inches=0.08)
    plt.close(yz_figure)

    summary={
        "dataset":"Aramco_1800",
        "shape":shape,
        "selection_source":"Fig. 7 field-level rate-distortion results",
        "1d4r_axis":2,
        "2d4r_axes":[1,2],
        "direction":"normalized central-difference gradient,canonicalized to nz>=0",
        "sampled_targets":int(coordinates.shape[0]),
        "plotted_targets":int(valid_index.size),
        "gradient_magnitude_q25":gradient_threshold,
        "slope_1d_q10":slope_1d_threshold,
        "slope_2d_q10":slope_2d_threshold,
        "1d4r_raw_t_quantiles":quantiles(t_1d_raw[valid]),
        "2d4r_raw_t_quantiles":quantiles(t_2d_raw[valid]),
        "1d4r_constrained_t_quantiles":quantiles(np.clip(t_1d_raw[valid],2/32,12/32)),
        "2d4r_constrained_t_quantiles":quantiles(np.clip(t_2d_raw[valid],-1/4,1/4)),
        "1d4r_lower_endpoint_fraction":float(np.mean(t_1d_raw[valid]<=2/32)),
        "1d4r_upper_endpoint_fraction":float(np.mean(t_1d_raw[valid]>=12/32)),
        "2d4r_lower_endpoint_fraction":float(np.mean(t_2d_raw[valid]<=-1/4)),
        "2d4r_upper_endpoint_fraction":float(np.mean(t_2d_raw[valid]>=1/4))
    }
    summary["raw_plot_abs_t_limits"]={"1d4r":raw_limit_1d,"2d4r":raw_limit_2d}
    with (output_dir/"summary.json").open("w") as output:
        json.dump(summary,output,indent=2)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
