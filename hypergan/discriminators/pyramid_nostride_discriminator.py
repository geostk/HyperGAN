import tensorflow as tf
import hyperchamber as hc
from hypergan.util.ops import *
from hypergan.util.globals import *
from hypergan.util.hc_tf import *
import hypergan.regularizers.minibatch_regularizer as minibatch_regularizer
import os

def config():
    selector = hc.Selector()
    selector.set("activation", [lrelu])#prelu("d_")])
    selector.set('regularizer', [layer_norm_1, batch_norm_1]) # Size of fully connected layers

    selector.set("layers", [4,5,3]) #Layers in D
    selector.set("depth_increase", [1,2,4])# Size increase of D's features on each layer

    selector.set('add_noise', [True]) #add noise to input
    selector.set('noise_stddev', [1e-1]) #the amount of noise to add - always centered at 0
    selector.set('regularizers', [[],[minibatch_regularizer.get_features]]) # these regularizers get applied at the end of D

    selector.set('create', discriminator)
    
    return selector.random_config()

def discriminator(root_config, config, x, g, xs, gs, prefix='d_'):
    activation = config['activation']
    batch_size = int(x.get_shape()[0])
    depth_increase = config['depth_increase']
    depth = config['layers']
    batch_norm = config['regularizer']

    if(config['add_noise']):
        x += tf.random_normal(x.get_shape(), mean=0, stddev=config['noise_stddev'], dtype=root_config['dtype'])

    net = x
    net = conv2d(net, 16, name=prefix+'_expand', k_w=3, k_h=3, d_h=1, d_w=1)

    xgs = []
    xgs_conv = []
    for i in range(depth):
      if batch_norm is not None:
          net = batch_norm(batch_size*2, name=prefix+'_expand_bn_'+str(i))(net)
      net = activation(net)
      # APPEND xs[i] and gs[i]
      if(i < len(xs) and i > 0):
        xg = tf.concat(0, [xs[i], gs[i]])
        xg += tf.random_normal(xg.get_shape(), mean=0, stddev=config['noise_stddev']*i, dtype=root_config['dtype'])

        xgs.append(xg)
  
        s = [int(x) for x in xg.get_shape()]

        net = tf.concat(3, [net, xg])
      filter_size_w = 2
      filter_size_h = 2
      filter = [1,filter_size_w,filter_size_h,1]
      stride = [1,filter_size_w,filter_size_h,1]
      net = conv2d(net, int(int(net.get_shape()[3])*depth_increase), name=prefix+'_expand_layer'+str(i), k_w=3, k_h=3, d_h=1, d_w=1)
      net = tf.nn.avg_pool(net, ksize=filter, strides=stride, padding='SAME')

      print('[discriminator] layer', net)

    k=-1
    if batch_norm is not None:
        net = batch_norm(batch_size*2, name=prefix+'_expand_bn_end_'+str(i))(net)
    net = activation(net)
    net = tf.reshape(net, [batch_size, -1])

    regularizers = []
    for regularizer in config['regularizers']:
        regs = regularizer(root_config, net, prefix)
        regularizers += regs

 
    return tf.concat(1, [net]+regularizers)


