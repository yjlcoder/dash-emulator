import logging


def config(verbose=False):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=logging.INFO)


def getLogger(name):
    return logging.getLogger(name)


config()
