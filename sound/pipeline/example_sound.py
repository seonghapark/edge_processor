#!/usr/bin/env python3

import pika
import json
import queue
import numpy as np
import logging
import uuid

import sys
# sys.path.append('../../image')
sys.path.append('/Users/theone/repo/edge_processor/image')
from processor import *

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


class RPCRequester(object):
    def __init__(self, my_routing_key):
        self.my_routing_key = my_routing_key
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.callback_queue = self.channel.queue_declare(exclusive=True).method.queue
        self.channel.basic_consume(self.on_response, queue=self.callback_queue)

    def close(self):
        self.channel.close()
        self.connection.close()

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def request(self, duration):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        message = {'reference': self.my_routing_key, 'command':'read', 'duration':duration}
        self.channel.basic_publish(
            exchange='',
            routing_key='audio_rpc',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id),
            body=json.dumps(message).encode())

        while self.response is None:
            self.connection.process_data_events()
        return self.response

import wave

def on_receive(method, props, body):
    message = Packet(body.decode())
    logger.info(message.meta_data)
    # logger.info(message.raw)
    # logger.info(len(message.raw))
    wf = wave.open('result.wav', 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(48000)
    wf.writeframes(message.raw)
    wf.close()

def main():
    sampling_interval = 30 # seconds
    wait_time_out = 60 # seconds

    my_routing_id = str(uuid.uuid4())
    logger.info('my routing id: %s' % (my_routing_id,))
    rpc = RPCRequester(my_routing_id)
    
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='sound_pipeline', type='direct')
    result = channel.queue_declare(exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='sound_pipeline', routing_key=my_routing_id)
    
    while True:
        logger.info('Request a 10 seconds sample')
        ret = rpc.request(10)
        logger.info(ret)
        if b'Ok' in ret:
            logger.info('Wait for the data for %s' % (my_routing_id,))
            time_out = time.time() + wait_time_out
            while time.time() < time_out: 
                method, header, body = channel.basic_get(queue=result.method.queue, no_ack=True)
                if method is not None:
                    logger.info('Received:%s ' % (str(header),))
                    on_receive(method, header, body)
                    break
                time.sleep(0.2)
            
            logger.info('Reception is done.')
        else:
            logger.error('Error on RPC request')
        time.sleep(sampling_interval)

    logger.info('Closing example sound...')
    channel.close()
    connection.close()
    rpc.close()

    
if __name__ == '__main__':
    main()
