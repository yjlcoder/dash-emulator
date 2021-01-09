import logging

class CsvFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        self.output = io.StringIO()
        self.writer = csv.writer(self.output, quoting=csv.QUOTE_ALL)

    def format(self, record):
        self.writer.writerow([record.levelname, record.msg])
        data = self.output.getvalue()
        self.output.truncate(0)
        self.output.seek(0)
        return data.strip()

def config(verbose=False):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=logging.INFO)

def getLogger(name):
    return logging.getLogger(name)


config()
