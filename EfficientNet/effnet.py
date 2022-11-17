# -*- coding: utf-8 -*-
"""Effnetv2b3_Homework1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1p0CRAZgkQAKrtNF-GZySlwgx-RdJOSVU

# EfficientNet
"""

learning_rate = 1e-3

import tensorflow as tf
import numpy as np
import os
import random
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics import confusion_matrix
import cv2

import os
import time 
from PIL import Image

import torch
import torchvision
import torch.nn as nn
import torch.nn.functional as F
from torchvision.transforms import ToTensor
from torchvision.utils import make_grid
from torch.utils.data.dataloader import DataLoader
from torch.utils.data import random_split

from keras.layers import Dense, Activation, Dropout, Flatten, Conv2D, MaxPooling2D
#from keras.layers.normalization import BatchNormalization
from keras.models import Sequential

tfk = tf.keras
tfkl = tf.keras.layers
print(tf.__version__)

# Random seed for reproducibility
seed = 42

random.seed(seed)
os.environ['PYTHONHASHSEED'] = str(seed)
np.random.seed(seed)
tf.random.set_seed(seed)
tf.compat.v1.set_random_seed(seed)

"""# Scelta CNN e creazione fully connected network"""

inputshape = [96, 96, 3]
effnet = tf.keras.applications.EfficientNetB3(include_top=False, input_shape=inputshape, weights = "imagenet")

for layer in effnet.layers:
	layer.trainable = True

"""Trying with two hidden layers"""

def create_model_085acc (input_shape, convnet):
  # mark loaded layers as not trainable

  dropout_rate = 0.2
  dropout_rate1 = 0.5

    # Build the model
  input_layer = convnet.layers[0].input
  flat1 = Flatten()(convnet.layers[-1].output)
  flat1 = tfkl.Dropout(dropout_rate, seed=seed)(flat1)
  hidden_layer1 = tfkl.Dense(units=512, activation='relu', name='Hidden1', #qui 8 e poi basta
                                kernel_initializer=tfk.initializers.HeUniform(seed=seed))(flat1)
  hidden_layer1 = tfkl.Dropout(dropout_rate, seed=seed)(hidden_layer1)
  hidden_layer2 = tfkl.Dense(units=256, activation='relu', name='Hidden2', 
                                kernel_initializer=tfk.initializers.HeUniform(seed=seed))(hidden_layer1)
  hidden_layer2 = tfkl.Dropout(dropout_rate1, seed=seed)(hidden_layer2)
  output = tfkl.Dense(units=8, activation='softmax', name='Output', 
                                kernel_initializer=tfk.initializers.HeUniform(seed=seed))(hidden_layer2)
    # Connect input and output through the Model class
  model = tfk.Model(inputs=input_layer, outputs=output, name='model')

    # Compile the model
  # qualcosa (reduce) on plateau
  opt = tfk.optimizers.Adam(learning_rate)
  model.compile(loss=tfk.losses.CategoricalCrossentropy(), optimizer=opt, metrics='accuracy')

    # Return the model
  return model

# summarize

model = create_model_085acc(input_shape = inputshape, convnet = effnet)
model.summary()

#tfk.utils.plot_model(model)

"""#  Splitting the dataset and Data augmentation"""

# Commented out IPython magic to ensure Python compatibility
# %cd /gdrive/My Drive

data_dir="training_data_final"
batch_size = 16
img_height = 96
img_width = 96

training_dir = data_dir
from keras_preprocessing.image import ImageDataGenerator
data_gen = ImageDataGenerator(rescale=1/255, validation_split=0.2)
aug_train_data_gen = ImageDataGenerator(rotation_range=30, 
                                        height_shift_range=50, 
                                        width_shift_range=50, 
                                        zoom_range=0.3, 
                                        horizontal_flip=True, 
                                        vertical_flip=True,  
                                        fill_mode='reflect',
                                        rescale=1/255, 
                                        validation_split=0.2)
train_gen = aug_train_data_gen.flow_from_directory(directory=training_dir,
                                               target_size=(96,96),
                                               color_mode='rgb',
                                               classes=None, # can be set to labels
                                               class_mode='categorical',
                                               batch_size=64,
                                               shuffle=True,
                                               seed=seed,
                                               subset="training")

valid_gen = data_gen.flow_from_directory(directory=training_dir,
                                               target_size=(96,96),
                                               color_mode='rgb',
                                               #classes=labels, # can be set to labels
                                               class_mode='categorical',
                                               batch_size=1,
                                               shuffle=True,
                                               seed=seed,
                                               subset="validation")

countclass=[0,0,0,0,0,0,0,0]
for i in train_gen.classes:
  countclass[i] = countclass[i] + 1;

print(countclass)

tot = len(train_gen.classes)

print(tot)

weights = np.zeros(8, dtype=float)
for x in range(8):
  weights[x] = tot/countclass[x]

weights = weights.astype(int)

print(weights)

from datetime import datetime

def create_folders_and_callbacks(model_name):

  exps_dir = os.path.join('efficientnet_experiments')
  if not os.path.exists(exps_dir):
      os.makedirs(exps_dir)

  now = datetime.now().strftime('%b%d_%H-%M-%S')

  exp_dir = os.path.join(exps_dir, model_name + '_' + str(now))
  if not os.path.exists(exp_dir):
      os.makedirs(exp_dir)
      
  callbacks = []

  # Model checkpoint
  # ----------------
  ckpt_dir = os.path.join(exp_dir, 'ckpts')
  if not os.path.exists(ckpt_dir):
      os.makedirs(ckpt_dir)

  ckpt_callback = tf.keras.callbacks.ModelCheckpoint(filepath=os.path.join(ckpt_dir, '{val_loss:.4f}-{loss:.4f}-f_model.h5'), 
                                                     save_weights_only=False, # True to save only weights
                                                     save_best_only=True, # True to save only the best epoch
                                                     monitor='accuracy')  
  callbacks.append(ckpt_callback)

  # Visualize Learning on Tensorboard
  # ---------------------------------
  tb_dir = os.path.join(exp_dir, 'tb_logs')
  if not os.path.exists(tb_dir):
      os.makedirs(tb_dir)
      
  # By default shows losses and metrics for both training and validation
  tb_callback = tf.keras.callbacks.TensorBoard(log_dir=tb_dir, 
                                               profile_batch=0,
                                               histogram_freq=1)  # if > 0 (epochs) shows weights histograms
  callbacks.append(tb_callback)

  # Early Stopping
  # --------------
  es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)
  callbacks.append(es_callback)

  return callbacks

"""# Training"""

callbacks = create_folders_and_callbacks(model_name='CNN_Effnet')

# Train the model
tl_history = model.fit(
    train_gen,
    epochs = 100,
    validation_data = valid_gen,
    class_weight = {0:19,  1:6,  2:6,  3:6,  4:6, 5:15,  6:6,  7:6},
    callbacks=callbacks
).history