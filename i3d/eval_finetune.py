# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Loads a sample video and classifies using a trained Kinetics checkpoint."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import numpy as np
import tensorflow as tf
from queue import Queue
import threading
import i3d.i3d as i3d
import cv2
import time
import os
import h5py
import helpers.paths as paths

_IMAGE_SIZE = 224
_BATCH_SIZE = 25

# _SAMPLE_VIDEO_FRAMES = 79
_SAMPLE_VIDEO_FRAMES = 25
# _SAMPLE_PATHS = {
#     'rgb': 'data/v_CricketShot_g04_c01_rgb.npy',
#     'flow': 'data/v_CricketShot_g04_c01_flow.npy',
# }

_CHECKPOINT_PATHS = {
    'rgb': '/nrs/branson/kwaki/data/models/checkpoints/rgb_scratch/model.ckpt',
    'rgb600': '/nrs/branson/kwaki/data/models/checkpoints/rgb_scratch_kin600/model.ckpt',
    'flow': '/nrs/branson/kwaki/data/models/checkpoints/flow_scratch/model.ckpt',
    'rgb_imagenet': '/nrs/branson/kwaki/data/models/checkpoints/rgb_imagenet/model.ckpt',
    'flow_imagenet': '/nrs/branson/kwaki/data/models/checkpoints/flow_imagenet/model.ckpt',
}

_LABEL_MAP_PATH = '/nrs/branson/kwaki/data/lists/label_map.txt'
_LABEL_MAP_PATH_600 = '/nrs/branson/kwaki/data/lists/data/label_map_600.txt'

FLAGS = tf.flags.FLAGS

# tf.flags.DEFINE_string('eval_type', 'joint', 'rgb, rgb600, flow, or joint')
tf.flags.DEFINE_string('eval_type', 'rgb', 'rgb, rgb600, flow, or joint')
tf.flags.DEFINE_boolean('imagenet_pretrained', True, '')
tf.flags.DEFINE_string('filelist', '', 'Text file with list of experiments.')
tf.flags.DEFINE_integer('gpus', 0, 'GPU to use.')
tf.flags.DEFINE_integer('window_start', -31, 'Offset from the desired frame.')
tf.flags.DEFINE_integer('window_size', 64, 'Window size.')
tf.flags.DEFINE_integer('batch_size', 10, 'Batch size.')
tf.flags.DEFINE_string('movie_dir', '', 'Movie folder.')
tf.flags.DEFINE_string('out_dir', '', 'Output folder.')
tf.flags.DEFINE_string('feat_key', '', 'new feature key name.')
tf.flags.DEFINE_string('logfile', '', 'log filename.')
tf.flags.DEFINE_string('model', '', 'model filename.')
tf.flags.DEFINE_string('type', '', 'front or side.')
tf.flags.DEFINE_float('learning_rate', 0.00001, 'placeholder.')
tf.flags.DEFINE_string('feat_dir', '', 'feature folder.')

def crop_frame(img, crop_size):
  # resize version
  img = np.array(cv2.resize(np.array(img),(crop_size, crop_size))).astype(np.float32)
  # also rescale the pixel values
  # the i3d network expects values between -1 and 1
  # img = img - img.min()
  # img = img / img.max() * 2
  # img = img - 1
  img = img / 255.0 * 2 - 1

  return img


def create_initial_batch(cap, crop_size, window_size, window_start):
  """Create the initial batch."""
  # loop for window start frames and add the first frame that many times.
  # then add window size - window start new frames.

  # print("\t\tFirst read")
  retval, frame = cap.read()
  # fill the list with num_frames_per_clip - 1.

  frame = crop_frame(frame, crop_size)
  # +1 cause the "center" frame in this case is the 0 frame.
  prev_frames = [frame for i in range(-window_start + 1)]

  window_end = window_size + window_start - 2
  frame_num = 1
  for i in range(window_end):
    retval, frame = cap.read()

    frame = crop_frame(frame, crop_size)
    prev_frames.append(frame)
    frame_num += 1

  return prev_frames, frame_num


def get_video_frames(batch_size, cap, num_frames, window_size=16, window_start=-8,
                     crop_size=112, queue=None, eval_type='rgb'):
  """Step through a video and provide frames in the queue."""
  # print("\t\tvideo grabber started.")
  # need a cache for the frames.
  # use a list cause it is easier to add and remove elements from it...

  prev_frames, frame_end = create_initial_batch(
    cap, crop_size, window_size, window_start)

  # loop over all the frames
  frame_num = 0
  while frame_num < num_frames:
    tic = time.time()
    # print("\t\tgetting batch")
    # build the batches.
    valid_len = np.min([num_frames - frame_num, batch_size])
    # (20, 16, 112, 112, 3)
    if eval_type == 'rgb':
      batch_frames = np.zeros(
        (batch_size, window_size, crop_size, crop_size, 3),
        dtype='float32'
      )
    else:
      batch_frames = np.zeros(
        (batch_size, window_size, crop_size, crop_size, 2),
        dtype='float32'
      )

    for i in range(valid_len):
      # if frame_end =< num_frames - 1:
      #   print("end!")
      # else:
      #   retval, frame = cap.read()
      if frame_end < num_frames:
        retval, frame = cap.read()
      # else, just use the previous frame (aka the last frame of the video)
      # else:
      #   print("\t\tend!")
      frame = crop_frame(frame, crop_size)
      prev_frames.append(frame)

      # batch_view1[i, :, :, :] = np.asarray(prev_views1) - np_mean
      # batch_view2[i, :, :, :] = np.asarray(prev_views2) - np_mean
      if eval_type == 'rgb':
        batch_frames[i, :, :, :] = np.asarray(prev_frames)
      else:
        batch_frames[i, :, :, :] = np.asarray(prev_frames)[:, :, :, :2]

      prev_frames.pop(0)
      frame_num += 1
      if frame_end < num_frames:
        frame_end +=1
    queue.put((valid_len, batch_frames, frame_num, frame_end))
    # print("\t\tbatch added: %f" % (time.time() - tic))

  # cap.release()
  return


def write_features(out_dir, queue, feat_key):
  """Thread writer"""
  print("writer started")
  # with open("/nrs/branson/kwaki/data/c3d/debug-train.txt", "w") as fid:
  while True:
    exp_name, features, logits = queue.get()
    # print(exp_name)
    if exp_name == "done":
      print("writer exiting done")
      return

    feature_file = os.path.join(out_dir, exp_name)
    # print(feature_file)
    # fid.write("%s\n" % feature_file)
    with h5py.File(feature_file, "w") as out_data:
      front_key = "%s" % feat_key
      out_data[front_key] = features
      side_key = "logits"
      out_data[side_key] = logits

  print("writer closing")


def main(unused_argv):
  tf.logging.set_verbosity(tf.logging.INFO)
  eval_type = FLAGS.eval_type
  filelist = FLAGS.filelist
  gpu_num = FLAGS.gpus
  window_size = FLAGS.window_size
  window_start = FLAGS.window_start
  batch_size = FLAGS.batch_size
  movie_dir = FLAGS.movie_dir
  out_dir = FLAGS.out_dir
  feat_key = FLAGS.feat_key
  logname = FLAGS.logfile

  imagenet_pretrained = FLAGS.imagenet_pretrained

  opts = {}
  opts["flags"] = FLAGS
  opts["argv"] = sys.argv
  paths.setup_output_space(opts)
  
  NUM_CLASSES = 400

  if eval_type not in ['rgb', 'flow']:
    raise ValueError('Bad `eval_type`, must be one of rgb, rgb600, flow, joint')

  new_labels = tf.placeholder(tf.float32, shape=(batch_size, 7))
  if eval_type in 'rgb':
    # RGB input has 3 channels.
    rgb_input = tf.placeholder(
        tf.float32,
        shape=(batch_size, window_size, _IMAGE_SIZE, _IMAGE_SIZE, 3))

    with tf.variable_scope('RGB'):
      rgb_model = i3d.InceptionI3d(
        NUM_CLASSES, spatial_squeeze=True, final_endpoint='Logits')

    rgb_vars = []
    rgb_logits = []
    for gpu_index in range(0, gpu_num):
      with tf.device('/gpu:%d' % gpu_index):
        _, rgb_endpoints = rgb_model(
          rgb_input[gpu_index * batch_size : (gpu_index + 1) * batch_size, :, :, :, :],
          is_training=False, dropout_keep_prob=1.0)
        rgb_vars.append(rgb_endpoints["averaged"])
        rgb_logits.append(rgb_endpoints["logit2"])
        # temp hack
        # rgb_logits = rgb_endpoints
    # rgb_endpoints = rgb_vars
    rgb_endpoints = [
      tf.concat(rgb_vars, 0),
      tf.concat(rgb_logits, 0)
    ]

    # remaping variables?
    rgb_variable_map = {}
    for variable in tf.global_variables():
      if variable.name.split('/')[0] == 'RGB':
        rgb_variable_map[variable.name.replace(':0', '')] = variable

    rgb_saver = tf.train.Saver(var_list=rgb_variable_map, reshape=True)

  if eval_type in 'flow':
    # Flow input has only 2 channels.
    rgb_input = tf.placeholder(
        tf.float32,
        shape=(batch_size, window_size, _IMAGE_SIZE, _IMAGE_SIZE, 2))
    with tf.variable_scope('Flow'):
      rgb_model = i3d.InceptionI3d(
          NUM_CLASSES, spatial_squeeze=True, final_endpoint='Logits')
      # rgb_logits, _ = rgb_model(
      #     rgb_input, is_training=False, dropout_keep_prob=1.0)

    rgb_vars = []
    rgb_logits = []
    for gpu_index in range(0, gpu_num):
      with tf.device('/gpu:%d' % gpu_index):
        _, rgb_endpoints = rgb_model(
          rgb_input[gpu_index * batch_size : (gpu_index + 1) * batch_size, :, :, :, :],
          is_training=False, dropout_keep_prob=1.0)
        rgb_vars.append(rgb_endpoints["averaged"])
        rgb_logits.append(rgb_endpoints["logit2"])
        # new_cost, optimizer = create_criterion(
        #   opts, rgb_logit, new_labels, weight=None,
        #   name="hantman_crit")
        # temp hack
        # rgb_logits = rgb_endpoints
    # rgb_endpoints = rgb_vars
    # rgb_endpoints = tf.concat(rgb_vars, 0)
    rgb_endpoints = [
      tf.concat(rgb_vars, 0),
      tf.concat(rgb_logits, 0)
    ]

    rgb_variable_map = {}
    for variable in tf.global_variables():
      if variable.name.split('/')[0] == 'Flow':
        rgb_variable_map[variable.name.replace(':0', '')] = variable
      # if variable.name.split('/')[0] == 'Flow':
      #   rgb_variable_map[variable.name.replace(':0', '')] = variable
    rgb_saver = tf.train.Saver(var_list=rgb_variable_map, reshape=True)

  # movie_dir = '/nrs/branson/kwaki/data/videos/hantman_split/front'
  # out_dir = "/nrs/branson/kwaki/data/test"
  # start writer thread
  feat_dir = opts["flags"].feat_dir  # os.path.join(out_dir, "features")
  if not os.path.isdir(feat_dir):
    os.makedirs(feat_dir)
  write_queue = Queue()
  writer_thread = threading.Thread(
    target=write_features,
    args=(feat_dir, write_queue, feat_key))
  writer_thread.start()

  with tf.Session() as sess:
    # sess.run(tf.global_variables_initializer())
    feed_dict = {}
    # for key in rgb_variable_map.keys():
    #   if 'Conv3d_1a_7x7' in key:
    #     print(key)
    #   # if 'hantman' in key:
    #   #   print(key)
    if eval_type in 'rgb':
      if imagenet_pretrained:
        rgb_saver.restore(sess, opts["flags"].model)
      else:
        rgb_saver.restore(sess, _CHECKPOINT_PATHS[eval_type])
      tf.logging.info('RGB checkpoint restored')
      # rgb_sample = np.load(_SAMPLE_PATHS['rgb'])
      # tf.logging.info('RGB data loaded, shape=%s', str(rgb_sample.shape))

    if eval_type in 'flow':
      if imagenet_pretrained:
        rgb_saver.restore(sess, opts["flags"].model)
      else:
        rgb_saver.restore(sess, _CHECKPOINT_PATHS['flow'])
      tf.logging.info('Flow checkpoint restored')
      # flow_sample = np.load(_SAMPLE_PATHS['flow'])
      # tf.logging.info('Flow data loaded, shape=%s', str(flow_sample.shape))
      # feed_dict[flow_input] = flow_sample

    # filename = "/nrs/branson/kwaki/data/hantman_pruned/M147_20150506_v017/movie_comb.avi"
    log_fid = open(logname, "w")
    with open(filelist, "r") as fid:
      exp_name = fid.readline().strip()
      # filename = os.path.join(movie_dir, exp_name, "movie_comb.avi")
      while exp_name:
        feature_file = os.path.join(out_dir, exp_name)
        if os.path.exists(feature_file):
          break

        print(exp_name)
        # filename = os.path.join(movie_dir, exp_name, "movie_comb.avi")
        all_tic = time.time()
        proc_tic = time.time()
        # filename = os.path.join(movie_dir, "front", "%s.avi" % exp_name)
        # print(filename)
        # front_fc, front_logit = process_video(
        #   sess, rgb_endpoints, rgb_input,
        #   batch_size * gpu_num, window_start, window_size,
        #   filename, eval_type)

        filename = os.path.join(movie_dir, opts["flags"].type, "%s.avi" % exp_name)
        print(filename)
        fc_feats, logits = process_video(
          sess, rgb_endpoints, rgb_input,
          batch_size * gpu_num, window_start, window_size,
          filename, eval_type)
        print("\tfinished feature computation: %f" % (time.time() - proc_tic))
        log_fid.write("%s,%f\n" % (exp_name, time.time() - proc_tic))
        log_fid.flush()

        # write_tic = time.time()
        write_queue.put((exp_name, fc_feats, logits))

        # print("\twrite sent: %f" % (time.time() - write_tic))
        # print("total time: %f" % (time.time() - all_tic))
        exp_name = fid.readline().strip()
  log_fid.close()
  write_queue.put(("done", [], []))
  print("waiting for join")
  writer_thread.join()


def process_video(sess, rgb_endpoints, rgb_input, batch_size,
                  window_start, window_size, filename, eval_type):
  """Create features for one video."""
  # print(filename)
  queue = Queue(maxsize=8)
  feed_dict = {}
  # get_video_frames(filename, batch_size, num_frames_per_clip=_IMAGE_SIZE, queue=queue)
  cap = cv2.VideoCapture(filename)
  num_frames = np.min([1500, int(cap.get(cv2.CAP_PROP_FRAME_COUNT))])
  # print(num_frames)
  # cap.release()

  # print("starting video thread...")
  video_thread = threading.Thread(
    target=get_video_frames,
    args=(batch_size, cap, num_frames),
    kwargs={
     'window_size': window_size,
     'window_start': window_start,
     'crop_size': _IMAGE_SIZE,
     'queue': queue,
     'eval_type': eval_type
    })
  video_thread.start()
  # print("started video thread!")

  frame_fc = np.zeros((num_frames, 7168))
  frame_logit = np.zeros((num_frames, 7))

  # print("proc'ing first batch")
  data = queue.get()
  frame_proc, frame_pred = sess.run(rgb_endpoints, {rgb_input:data[1]})
  frame_fc[:batch_size, :] = frame_proc
  frame_logit[:batch_size, :] = frame_pred

  start_frame = batch_size
  while start_frame < num_frames:
    # print("processing batch")
    batch_tic = time.time()
    data = queue.get()
    frame_proc, frame_pred = sess.run(rgb_endpoints, {rgb_input:data[1]})
    # print(data[3)
    # print(data[4])

    valid_len = data[0]
    end_frame = valid_len + start_frame
    frame_fc[start_frame:end_frame, :] = frame_proc[:valid_len, :]
    frame_logit[start_frame:end_frame, :] = frame_pred[:valid_len, :]

    start_frame += valid_len
    # print("batch processed: %f" % (time.time() - batch_tic))

  video_thread.join()
  cap.release()

  # if np.any(np.argmax(frame_logit, axis=1) != 6):
  #   import pdb; pdb.set_trace()

  return frame_fc, frame_logit


def create_criterion(opts, endpoint, labels, weight=None, name=None):
  cost = tf.nn.softmax_cross_entropy_with_logits_v2(
    logits=endpoint,
    labels=labels
  )

  if weight is not None:
    label_weights = tf.reduce_sum(labels * weight, axis=1)
    cost = label_weights * cost

  cost = tf.reduce_mean(cost)
  if name is not None:
    # optim = tf.train.GradientDescentOptimizer(
    #   opts["flags"].learning_rate, name=name).minimize(cost)
    optim = tf.train.AdamOptimizer(
      opts["flags"].learning_rate, name=name).minimize(cost)
  else:
    optim = tf.train.GradientDescentOptimizer(
      opts["flags"].learning_rate).minimize(cost)
  return cost, optim



def compute_features(sess, feat_var, images_var, batch_views):
  """Compute the features using the feat_var."""
  # view1_fc6, view1_fc7 = sess.run(feat_var, {images_placeholder:batch_view1})
  view1_fc = sess.run(feat_var, {images_var:batch_views[0]})
  view2_fc = sess.run(feat_var, {images_var:batch_views[1]})
  return view1_fc, view2_fc


if __name__ == '__main__':
  tf.app.run(main)
