"""
You are encouraged to edit this file during development, however your final
model must be trained using the original version of this file. This file
trains the model defined in implementation.py, performs tensorboard logging,
and saves the model to disk every 10000 iterations. It also prints loss
values to stdout every 50 iterations.
"""


import numpy as np
import tensorflow as tf
from random import randint
import datetime
import os

import implementation as imp

batch_size = imp.batch_size
iterations = 100000
seq_length = 40  # Maximum length of sentence

checkpoints_dir = "./checkpoints"

def getTrainBatch():
    labels = []
    arr = np.zeros([batch_size, seq_length])
    for i in range(batch_size):
        if (i % 2 == 0):
            num = randint(0, 9999)
            labels.append([1, 0])
        else:
            num = randint(12500, 22499)
            labels.append([0, 1])
        arr[i] = training_data[num]
    return arr, labels

def getValidBatch():
    labels = []
    arr = np.zeros([2500, seq_length])
    for i in range(2500):
        arr[i] = training_data[10000 + i]
        labels.append([1, 0])
    for i in range(2500):
        arr[i] = training_data[22500 + i]
        labels.append([0, 1])
    return arr, labels

# Call implementation
glove_array, glove_dict = imp.load_glove_embeddings()
training_data = imp.load_data(glove_dict)
input_data, labels, optimizer, accuracy, loss = imp.define_graph(glove_array)

# tensorboard
train_accuracy_op = tf.summary.scalar("training_accuracy", accuracy)
test_accuracy_op = tf.summary.scalar("test_accuracy", accuracy)
loss_op = tf.summary.scalar("loss", loss)
summary_op = tf.summary.merge([train_accuracy_op, loss_op])

# saver
all_saver = tf.train.Saver()

sess = tf.InteractiveSession()
sess.run(tf.global_variables_initializer())

logdir = "tensorboard/" + datetime.datetime.now().strftime(
    "%Y%m%d-%H%M%S") + "/"
writer = tf.summary.FileWriter(logdir, sess.graph)

for i in range(iterations):
    batch_data, batch_labels = getTrainBatch()
    sess.run(optimizer, {input_data: batch_data, labels: batch_labels})
    if (i % 50 == 0):
        loss_value, accuracy_value, summary = sess.run(
            [loss, accuracy, summary_op],
            {input_data: batch_data,
             labels: batch_labels})
        writer.add_summary(summary, i)

        # run on test data
        test_data, test_labels = getValidBatch()
        test_acc, test_summ = sess.run(
            [accuracy, test_accuracy_op],
            {input_data: test_data,
             labels: test_labels})
        writer.add_summary(test_summ, i)

        print("Iteration: ", i)
        print("loss", loss_value)
        print("acc", accuracy_value)
        print("test acc", test_acc)
    if (i % 10000 == 0 and i != 0):
        if not os.path.exists(checkpoints_dir):
            os.makedirs(checkpoints_dir)
        save_path = all_saver.save(sess, checkpoints_dir +
                                   "/trained_model.ckpt",
                                   global_step=i)
        print("Saved model to %s" % save_path)
sess.close()
