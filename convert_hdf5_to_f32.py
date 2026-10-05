#!/usr/bin/env python3

import argparse
import os
from pathlib import Path

import h5py
import hdf5plugin
import numpy as np


def parse_shape(text):
    try:
        shape=tuple(int(value) for value in text.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("shape must contain comma-separated integers") from error
    if not shape or any(value<=0 for value in shape):
        raise argparse.ArgumentTypeError("shape dimensions must be positive")
    return shape


def main():
    parser=argparse.ArgumentParser(description="Stream an HDF5 dataset into a raw float32 file")
    parser.add_argument("source",type=Path)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--dataset",required=True)
    parser.add_argument("--shape",type=parse_shape,required=True)
    parser.add_argument("--chunk-size",type=int,default=8)
    arguments=parser.parse_args()
    if arguments.chunk_size<=0:
        parser.error("--chunk-size must be positive")

    expected_size=int(np.prod(arguments.shape,dtype=np.uint64))*np.dtype(np.float32).itemsize
    if arguments.destination.is_file() and arguments.destination.stat().st_size==expected_size:
        print(f"Existing output has the expected size: {arguments.destination}",flush=True)
        return

    temporary_path=arguments.destination.with_name(arguments.destination.name+f".tmp.{os.getpid()}")
    arguments.destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        with h5py.File(arguments.source,"r") as source_file:
            dataset=source_file[arguments.dataset]
            if tuple(dataset.shape)!=arguments.shape:
                raise ValueError(f"dataset shape {dataset.shape} does not match expected shape {arguments.shape}")
            with open(temporary_path,"wb") as destination_file:
                for begin in range(0,arguments.shape[0],arguments.chunk_size):
                    end=min(begin+arguments.chunk_size,arguments.shape[0])
                    np.asarray(dataset[begin:end],dtype=np.float32).tofile(destination_file)
                    if begin==0 or end==arguments.shape[0] or end%(arguments.chunk_size*32)==0:
                        print(f"Converted {end}/{arguments.shape[0]} slabs",flush=True)
        if temporary_path.stat().st_size!=expected_size:
            raise RuntimeError(f"output size {temporary_path.stat().st_size} does not match expected size {expected_size}")
        os.replace(temporary_path,arguments.destination)
        print(f"Wrote {arguments.destination} ({expected_size} bytes)",flush=True)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


if __name__=="__main__":
    main()
