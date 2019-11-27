class SpeedMonitor(object):
    def __init__(self):
        pass

    def feed(self, data, time):
        print("download data %d bytes in %d sec" % (data, time))
