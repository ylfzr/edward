#!/usr/bin/env python
"""Adversarially Learned Inference (Dumoulin et al., 2017), aka
  Bidirectional Generative Adversarial Networks (Donahue et al., 2017),
  for joint learning of generator and inference networks for MNIST.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import edward as ed
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import os
import tensorflow as tf

from tensorflow.contrib import slim
from tensorflow.examples.tutorials.mnist import input_data


M = 100  # batch size during training
d = 50  # latent dimension
leak = 0.2  # leak parameter for leakyReLU
hidden_units = 300
encoder_variance = 0.01  # Set to 0 for deterministic encoder


def leakyrelu(x, alpha=leak):
    return tf.maximum(x, alpha * x)


def gen_latent(x, hidden_units):
  h = slim.fully_connected(x, hidden_units, activation_fn=leakyrelu)
  z = slim.fully_connected(h, d, activation_fn=None)
  return z + np.random.normal(0, encoder_variance, np.shape(z))


def gen_data(z, hidden_units):
  h = slim.fully_connected(z, hidden_units, activation_fn=leakyrelu)
  x = slim.fully_connected(h, 784, activation_fn=tf.sigmoid)
  return x


def discriminative_network(x, y):
  #  Discriminator must output probability in logits
  inputs = tf.concat([x, y], 1)
  h1 = slim.fully_connected(inputs, hidden_units, activation_fn=leakyrelu)
  logit = slim.fully_connected(h1, 1, activation_fn=None)
  return logit


def plot(samples):
  fig = plt.figure(figsize=(4, 4))
  plt.title(str(samples))
  gs = gridspec.GridSpec(4, 4)
  gs.update(wspace=0.05, hspace=0.05)

  for i, sample in enumerate(samples):
    ax = plt.subplot(gs[i])
    plt.axis('off')
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_aspect('equal')
    plt.imshow(sample.reshape(28, 28), cmap='Greys_r')

  return fig


ed.set_seed(42)

DATA_DIR = "data/mnist"
IMG_DIR = "img"

if not os.path.exists(DATA_DIR):
  os.makedirs(DATA_DIR)
if not os.path.exists(IMG_DIR):
  os.makedirs(IMG_DIR)

# DATA. MNIST batches are fed at training time.
mnist = input_data.read_data_sets(DATA_DIR, one_hot=True)
x_ph = tf.placeholder(tf.float32, [M, 784])
z_ph = tf.placeholder(tf.float32, [M, d])

# MODEL
with tf.variable_scope("Gen"):
  xf = gen_data(z_ph, hidden_units)
  zf = gen_latent(x_ph, hidden_units)

# INFERENCE:
optimizer = tf.train.AdamOptimizer()
optimizer_d = tf.train.AdamOptimizer()
inference = ed.BiGANInference(
    latent_vars={zf: z_ph}, data={xf: x_ph},
    discriminator=discriminative_network)

inference.initialize(
    optimizer=optimizer, optimizer_d=optimizer_d, n_iter=100000, n_print=3000)

sess = ed.get_session()
init_op = tf.global_variables_initializer()
sess.run(init_op)

idx = np.random.randint(M, size=16)
i = 0
for t in range(inference.n_iter):
  if t % inference.n_print == 1:

    samples = sess.run(xf, feed_dict={z_ph: z_batch})
    samples = samples[idx, ]
    fig = plot(samples)
    plt.savefig(os.path.join(IMG_DIR, '{}{}.png').format(
        'Generated', str(i).zfill(3)), bbox_inches='tight')
    plt.close(fig)

    fig = plot(x_batch[idx, ])
    plt.savefig(os.path.join(IMG_DIR, '{}{}.png').format(
        'Base', str(i).zfill(3)), bbox_inches='tight')
    plt.close(fig)

    zsam = sess.run(zf, feed_dict={x_ph: x_batch})
    reconstructions = sess.run(xf, feed_dict={z_ph: zsam})
    reconstructions = reconstructions[idx, ]
    fig = plot(reconstructions)
    plt.savefig(os.path.join(IMG_DIR, '{}{}.png').format(
        'Reconstruct', str(i).zfill(3)), bbox_inches='tight')
    plt.close(fig)

    i += 1

  x_batch, _ = mnist.train.next_batch(M)
  z_batch = np.random.normal(0, 1, [M, d])

  info_dict = inference.update(feed_dict={x_ph: x_batch, z_ph: z_batch})
  inference.print_progress(info_dict)
