import os.path
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlparse

from dash_emulator.logger import getLogger

log = getLogger(__name__)


class Representation(object):
    def __init__(self, tree, adapatationSet):
        self._id = None
        self._bandwidth = None
        self._width = None
        self._height = None
        self._mime = None
        self._codec = None

        self._adapatationSet = adapatationSet  # type: AdaptationSet

        self.initialization = None
        self.media = None
        self.startNumber = None

        self.durations = None  # type: Optional[List[float]]
        self.urls = None  # type: Optional[List[str]]

        self.baseurl = None

        self.is_inited = False

        self.parse(tree)

    @property
    def id(self):
        return self._id

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

    def parse(self, tree):
        base = urlparse(self._adapatationSet.mpd.link)
        basepath = os.path.dirname(base.path)

        self._id = tree.attrib['id']
        self._mime = tree.attrib['mimeType']
        self._codec = tree.attrib['codecs']
        self._bandwidth = tree.attrib['bandwidth']
        if 'width' in tree.attrib:
            self._width = tree.attrib['width']
        if 'height' in tree.attrib:
            self._height = tree.attrib['height']

        segmentTemplate = tree.find("{%s}SegmentTemplate" % self._adapatationSet.mpd.namespace)
        self.initialization = segmentTemplate.attrib["initialization"].replace("$RepresentationID$",
                                                                               str(self.id))
        self.initialization = base._replace(path=os.path.join(basepath, self.initialization)).geturl()
        self.media = segmentTemplate.attrib['media']
        self.startNumber = int(segmentTemplate.attrib['startNumber'])
        self.timescale = int(segmentTemplate.attrib['timescale'])

        self.durations = [None] * self.startNumber
        self.urls = [None] * self.startNumber

        segmentTimeline = segmentTemplate.find("{%s}SegmentTimeline" % self._adapatationSet.mpd.namespace)

        num = self.startNumber
        for segment in segmentTimeline:
            self.durations.append(float(segment.attrib['d']) / self.timescale)
            filename = re.sub(r"\$Number(\%\d+d)\$", r"\1", self.media.replace("$RepresentationID$", str(self.id)))
            filename = filename % num
            self.urls.append(base._replace(path=os.path.join(basepath, filename)).geturl())

            if 'r' in segment.attrib:
                for i in range(int(segment.attrib['r'])):
                    num += 1
                    self.durations.append(float(segment.attrib['d']))
                    filename = re.sub(r"\$Number(\%\d+d)\$", r"\1",
                                      self.media.replace("$RepresentationID$", str(self.id)))
                    filename = filename % num
                    self.urls.append(base._replace(path=os.path.join(basepath, filename)).geturl())

            num += 1


class AdaptationSet(object):
    def __init__(self, tree, mpd):
        self.tree = tree
        self.id = None  # type: Optional[int]
        self.representations = []  # type: List[Representation]
        self.mpd = mpd  # type: MPD

        self.parse()

    def parse(self):
        self.id = self.tree.attrib['id']
        for representation in self.tree:
            self.representations.append(Representation(representation, self))


class MPD(object):
    def __init__(self, content: str, link):
        self.content = content
        self.link = link

        self.type = None
        self.namespace = None
        self.mediaPresentationDuration = None  # type: Optional[float]
        self.minBufferTime = None  # type: Optional[int]
        self.videoAdaptationSet = None  # type: Optional[AdaptationSet]
        self.audioAdaptationSet = None  # type: Optional[AdaptationSet]

        self.parse()

    def parse(self):
        def ISO8601TimeParse(duration):
            pattern = r"^PT(?:(\d+(?:.\d+)?)H)?(?:(\d+(?:.\d+)?)M)?(?:(\d+(?:.\d+)?)S)?$"
            results = re.match(pattern, duration)
            dur = [float(i) if i is not None else 0 for i in results.group(1, 2, 3)]
            dur = 3600 * dur[0] + 60 * dur[1] + dur[2]
            return dur

        root = ET.fromstring(self.content)
        pattern = r"^\{([\s\S]+)\}[\s\S]+$"
        self.namespace = re.match(pattern, root.tag).group(1)

        # type
        self.type = root.attrib["type"]

        # mediaPresentationDuration
        if "mediaPresentationDuration" in root.attrib:
            mediaPresentationDuration = root.attrib["mediaPresentationDuration"]
            self.mediaPresentationDuration = ISO8601TimeParse(mediaPresentationDuration)

        # minBuffer
        if "minBufferTime" in root.attrib:
            minBufferTime = root.attrib["minBufferTime"]
            self.minBufferTime = ISO8601TimeParse(minBufferTime)

        period = root.find("{%s}Period" % self.namespace)
        if period is None:
            log.error("[Parse MPD] Cannot find \"Period\" tag")
            exit(1)

        for adapationSet in period:
            contentType = adapationSet.attrib["contentType"]
            if contentType == 'video':
                self.videoAdaptationSet = AdaptationSet(adapationSet, self)
            elif contentType == 'audio':
                self.audioAdaptationSet = AdaptationSet(adapationSet, self)
            else:
                log.error("[Parse MPD] Unsupported content type in AdaptationSet: %s" % contentType)
