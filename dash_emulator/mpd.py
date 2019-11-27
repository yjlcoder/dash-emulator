from typing import List, Optional


class Representation():
    def __init__(self, id, bandwidth, width, height, codec):
        self._id = id
        self._bandwidth = bandwidth
        self._width = width
        self._height = height
        self._codec = codec

    @property
    def id(self):
        return self.id

    @property
    def bandwidth(self):
        return self._bandwidth

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def codec(self):
        return self._codec


class MPD():
    def __init__(self, content: str):
        self.content = content

        self.mediaPresentationDuration = None  # type: Optional[int]
        self.minBufferTime = None  # type: Optional[int]
        self.videoRepresentations = []  # type: List[Representation]
        self.audioRepresentations = []  # type: List[Representation]

        self.parse(self.content)

    def parse(self, content):
        # TODO
        pass
