import tensorflow as tf
import numpy as np
import glob #this will be useful when reading reviews from file
import os
import tarfile
import re
import string
import math

# Using tensorflow 1.3.0

batch_size = 50
GLOVE_DIM = 50
GLOVE_MAX_VOCAB = 10000  # 400000 words in glove datasete
NUM_REVIEWS = 25000
WORDS_PER_REVIEW = 40

# global hyperparameters
DROPOUT_KEEP_PROB = 0.75

# RNN hyperparameters
LSTM_SIZE = 16
RNN_LAYERS = 2
LEARNING_RATE = 0.005

# binary classifier hyperparameters
BIN_CLASS_HIDDEN_SIZE = 32

def preprocess(rawstring):
    # stopwords
    stops = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
        'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
        'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
        'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who',
        'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was',
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
        'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
        'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
        'about', 'against', 'between', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
        'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
        'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'only', 'own', 'same', 'so', 'than', 'too', 'can', 'will'}

    nobr = re.sub(r'<br>', ' ', rawstring)
    no_punct = ''.join(c for c in nobr if c not in string.punctuation)
    lower = no_punct.lower()
    words = lower.split()
    processed = []
    for w in words:
        if w not in stops: continue
        processed.append(w)

    return processed


def load_data(glove_dict):
    """
    Take reviews from text files, vectorize them, and load them into a
    numpy array. Any preprocessing of the reviews should occur here. The first
    12500 reviews in the array should be the positive reviews, the 2nd 12500
    reviews should be the negative reviews.
    RETURN: numpy array of data with each row being a review in vectorized
    form"""

    filename = 'reviews.tar.gz'
    dir = os.path.dirname(__file__)

    # just load data if already there
    if os.path.exists(os.path.join(dir, 'data.npy')):
        print("using saved data, delete 'data.npy' to reprocess")
        data = np.load('data.npy')
        return data

    # untar
    if not os.path.exists(os.path.join(dir, 'reviews/')):
        with tarfile.open(filename, "r") as tarball:
            tarball.extractall(os.path.join(dir, 'reviews/'))

    # load and preprocess
    file_list = glob.glob(os.path.join(dir, 'reviews/pos/*'))
    file_list.extend(glob.glob(os.path.join(dir, 'reviews/neg/*')))
    assert(len(file_list) == NUM_REVIEWS)
    data = np.empty([NUM_REVIEWS, WORDS_PER_REVIEW], dtype=np.intp)
    filenum = 0
    for f in file_list:
        with open(f, "r", encoding='utf8') as openf:
            s = openf.read()
            words = preprocess(s)
            word_indices = []
            wordnum = 0
            for w in words:
                if wordnum >= WORDS_PER_REVIEW: break
                if w in glove_dict:
                    # add index of known word
                    word_indices.append(glove_dict[w]) 
                else:
                    # add the index of the unknown word
                    word_indices.append(glove_dict['UNK'])
                wordnum += 1

            # zero padding
            if wordnum < WORDS_PER_REVIEW:
                for i in range(wordnum, WORDS_PER_REVIEW):
                    word_indices.append(0)

            data[filenum] = word_indices
        filenum += 1
        
    np.save("data", data)

    return data


def load_glove_embeddings():
    """
    Load the glove embeddings into a array and a dictionary with words as
    keys and their associated index as the value. Assumes the glove
    embeddings are located in the same directory and named "glove.6B.50d.txt"
    RETURN: embeddings: the array containing word vectors
            word_index_dict: a dictionary matching a word in string form to
            its index in the embeddings array. e.g. {"apple": 119"}
    """

    #if you are running on the CSE machines, you can load the glove data from here
    #data = open("/home/cs9444/public_html/17s2/hw2/glove.6B.50d.txt",'r',encoding="utf-8")
    
    with open("glove.6B.50d.txt",'r',encoding="utf-8") as f:
        data = f.readlines()

    embeddings = np.empty([GLOVE_MAX_VOCAB,GLOVE_DIM], dtype=np.float32)
    word_index_dict = {}

    word_index_dict['UNK'] = 0
    embeddings[0] = np.zeros(GLOVE_DIM)

    n = 1
    for d in data:
        if n >= GLOVE_MAX_VOCAB:
            break
        elements = d.split()
        word_index_dict[elements[0]] = n
        embeddings[n] = elements[1:]
        n += 1

    return embeddings, word_index_dict

def lstm_cell():
    cell = tf.nn.rnn_cell.BasicLSTMCell(LSTM_SIZE, forget_bias = 0.0, 
        state_is_tuple = True)
    cell = tf.nn.rnn_cell.DropoutWrapper(cell, DROPOUT_KEEP_PROB)
    return cell

def onelayer(input_tensor):
    output = tf.layers.dense(input_tensor, 2, name = "bin_class_layer_1")
    return output

def twolayer(input_tensor):
    layer_one_output = tf.layers.dense(input_tensor, BIN_CLASS_HIDDEN_SIZE, 
        name = "bin_class_layer_1")
    layer_one_output = tf.nn.dropout(layer_one_output, DROPOUT_KEEP_PROB)
    output = tf.layers.dense(layer_one_output, 2, 
        name = "bin_class_layer_2")
    return output

def define_graph(glove_embeddings_arr):
    """
    Define the tensorflow graph that forms your model. You must use at least
    one recurrent unit. The input placeholder should be of size [batch_size,
    40] as we are restricting each review to it's first 40 words. The
    following naming convention must be used:
        Input placeholder: name="input_data"
        labels placeholder: name="labels"
        accuracy tensor: name="accuracy"
        loss tensor: name="loss"

    RETURN: input placeholder, labels placeholder, optimizer, accuracy and loss
    tensors"""

    input_data = tf.placeholder(tf.int32,
        shape = (batch_size, WORDS_PER_REVIEW), name = "input_data")
    labels = tf.placeholder(tf.int32, shape = (batch_size, 2), name = "labels")

    # substitute embeddings for word indices
    embeddings = tf.constant(glove_embeddings_arr, name = "embeddings")
    input_embeddings = tf.nn.embedding_lookup(embeddings, input_data, 
        name = "input_embeddings")

    # dropout on inputs
    input_embeddings = tf.nn.dropout(input_embeddings, DROPOUT_KEEP_PROB, 
        name = "input_dropout")

    # multilayer lstm cell
    stacked_lstm_cell = tf.nn.rnn_cell.MultiRNNCell(
        [lstm_cell() for _ in range(RNN_LAYERS)], 
        state_is_tuple = True)

    outputs, last_states = tf.nn.dynamic_rnn(
        cell = stacked_lstm_cell,
        dtype = tf.float32, 
        sequence_length = tf.fill([batch_size], WORDS_PER_REVIEW), 
        inputs = input_embeddings)

    output = tf.reshape(tf.concat(outputs, 1), 
        [batch_size, LSTM_SIZE * WORDS_PER_REVIEW])

    # rnn to layer 1 dropout
    output = tf.nn.dropout(output, DROPOUT_KEEP_PROB, 
        name = "rnn_to_layer_1_dropout")

    # one-layer binary classifier
    #logits = onelayer(output)

    # two-layer binary classifier
    logits = twolayer(output)
    
    # stats
    preds = tf.argmax(logits, 1, output_type = tf.int32, name = "predictions")
    label_argmax = tf.argmax(labels, 1, output_type = tf.int32, 
        name = "label_argmax")
    correct = tf.equal(label_argmax, preds, name = "correct")
    accuracy = tf.reduce_mean(tf.cast(correct, tf.float32), name = "accuracy")
    
    # binary cross-entropy loss
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(
        labels = labels, logits = logits, name = "softmax_cross_entropy")
    loss = tf.reduce_mean(cross_entropy, name = "loss")

    # optimiser
    optimizer = tf.train.AdamOptimizer(LEARNING_RATE).minimize(loss)

    return input_data, labels, optimizer, accuracy, loss
