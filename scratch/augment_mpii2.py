"""Based off of convert_hantman_data.py"""
from __future__ import print_function,division
import numpy
import argparse
import h5py
import scipy.io as sio
from scipy import signal
import helpers.paths as paths
# import helpers.git_helper as git_helper
import os
import time
import torchvision.models as models
import torchvision.transforms as transforms
import torch
from torch.autograd import Variable
import PIL
import cv2
import cv
import sys

rng = numpy.random.RandomState(123)

# g_all_exp_dir = "/mnt/"
# labels_dir = "/media/drive3/kwaki/data/mpiicooking2/labels"
labels_dir = "/media/drive3/kwaki/data/mpiicooking2/temp_data/label_files"
videos_dir = "/media/drive3/kwaki/data/mpiicooking2/videos"
out_dir = "/media/drive3/kwaki/data/mpiicooking2/temp_data/hdf5"
batch_size = 50

# labels...labels
all_labels = ["take outV", "moveV", "addV", "washV", "cut apartV", "shakeV", "put inV", "pull apartV", "sliceV", "throw in garbageV", "peelV", "put onV", "stirV", "closeV", "enterV"]


def create_labels(num_frames, label_idx, label_frames):
    smooth_window = 19
    smooth_std = 2
    conv_filter = signal.gaussian(smooth_window, std=smooth_std)
    # print conv_filter.shape
    # print labels.shape
    labels = numpy.zeros((num_frames, 1, len(all_labels)))
    org_labels = numpy.zeros((num_frames, len(all_labels)))

    # for each activity fill the label matrix
    for i in range(len(label_idx)):
        frame = label_frames[i]
        behav = label_idx[i]

        labels[frame, 0, behav] = 1
        org_labels[frame, behav] = 1

    for i in range(labels.shape[2]):
        labels[:, 0, i] = numpy.convolve(labels[:, 0, i], conv_filter, 'same')
    return labels, org_labels


def process_file(filename):
    label_path = os.path.join(labels_dir, filename)

    label_names = []
    label_idx = []
    label_frames = []
    with open(label_path, "r") as fd:
        for line in fd:
            parsed = line.strip().split(',')
            try:
                idx = all_labels.index(parsed[1])
            except:
                import pdb; pdb.set_trace()
            label_idx.append(idx)
            label_names.append(parsed[1])
            label_frames.append(int(parsed[0]))

    labels = []
    org_labels = []
    h5_name = os.path.join(out_dir, "exps", filename[:-4])
    with h5py.File(h5_name, "a") as h5_data:
        num_frames = h5_data["vgg"].shape[0]
        labels, org_labels = create_labels(num_frames, label_idx, label_frames)
        h5_data["labels"] = labels
        h5_data["org_labels"] = org_labels


def main():
    # first get file list. extension, and add the movie extension
    filenames = os.listdir(labels_dir)
    filenames.sort()

    for filename in filenames:
        tic = time.time()
        process_file(filename)
        print(time.time() - tic)
        # import pdb; pdb.set_trace()


if __name__ == "__main__":
    # opts = setup_opts(opts)
    paths.create_dir(out_dir)
    paths.create_dir(os.path.join(out_dir, "exps"))
    paths.save_command2(out_dir, sys.argv)

    main()
