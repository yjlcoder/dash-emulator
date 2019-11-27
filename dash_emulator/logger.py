import logging


def config():
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%d-%m %H:%M:%S')


def getLogger(name):
    return logging.getLogger(name)
