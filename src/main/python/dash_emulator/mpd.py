import operator
import os.path
import re
import xml.etree.ElementTree as ET
from enum import Enum
from typing import List, Optional, Dict
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

        self.initialization_url = None  # type: Optional[str]
        self.media = None
        self.startNumber = None  # type: Optional[int]

        self.durations = None  # type: Optional[List[float]]
        self.urls = None  # type: Optional[List[str]]

        self.baseurl = None

        self.is_inited = False  # type: bool
        self.init_filename = None  # type: Optional[str]

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

    @property
    def mime(self):
        return self._mime

    def parse(self, tree):
        base = urlparse(self._adapatationSet.mpd.link)
        basepath = os.path.dirname(base.path)

        self._id = tree.attrib['id']
        self._mime = tree.attrib['mimeType']
        self._codec = tree.attrib['codecs']
        self._bandwidth = int(tree.attrib['bandwidth'])
        if 'width' in tree.attrib:
            self._width = tree.attrib['width']
        if 'height' in tree.attrib:
            self._height = tree.attrib['height']

        segmentTemplate = tree.find("{%s}SegmentTemplate" % self._adapatationSet.mpd.namespace)
        self.initialization_url = segmentTemplate.attrib["initialization"].replace("$RepresentationID$",
                                                                                   str(self.id))
        self.initialization_url = base._replace(path=os.path.join(basepath, self.initialization_url)).geturl()
        self.media = segmentTemplate.attrib['media']
        self.startNumber = int(segmentTemplate.attrib['startNumber'])
        self.timescale = int(segmentTemplate.attrib['timescale'])

        self.durations = [None] * self.startNumber  # type: List[Optional[int]]
        self.urls = [None] * self.startNumber  # type: List[Optional[int]]

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
                    self.durations.append(float(segment.attrib['d']) / self.timescale)
                    filename = re.sub(r"\$Number(\%\d+d)\$", r"\1",
                                      self.media.replace("$RepresentationID$", str(self.id)))
                    filename = filename % num
                    self.urls.append(base._replace(path=os.path.join(basepath, filename)).geturl())

            num += 1


class AdaptationSet(object):
    class ContentType(Enum):
        VIDEO = 1
        AUDIO = 2

    def __init__(self, tree, mpd):
        self.tree = tree
        self.id = None  # type: Optional[str]
        self.representations = []  # type: List[Representation]
        self.srd_info = None
        self.mpd = mpd  # type: MPD
        self.content_type = None  # type: Optional[AdaptationSet.ContentType]

        self.parse()

    def parse(self):
        self.id = self.tree.attrib['id']
        self.content_type = AdaptationSet.ContentType.VIDEO if self.tree.attrib['contentType'] == 'video' \
            else AdaptationSet.ContentType.AUDIO
        for representation in self.tree:
            # By far, only SRD info uses the tag "SupplementalProperty"
            if "SupplementalProperty" in representation.tag:
                self.srd_info = representation.attrib["value"]
            else:
                self.representations.append(Representation(representation, self))
        self.representations.sort(key=operator.attrgetter('bandwidth'))


class MPD(object):
    def __init__(self, content: str, link):
        self.content = content
        self.link = link

        self.type = None
        self.namespace = None
        self.mediaPresentationDuration = None  # type: Optional[float]
        self.minBufferTime = None  # type: Optional[float]
        self.adaptationSets = {}  # type: Dict[str, AdaptationSet]

        self.parse()

    def parse(self):
        def ISO8601TimeParse(duration):
            pattern = r"^PT(?:(\d+(?:.\d+)?)H)?(?:(\d+(?:.\d+)?)M)?(?:(\d+(?:.\d+)?)S)?$"
            results = re.match(pattern, duration)
            dur = [float(i) if i is not None else 0 for i in results.group(1, 2, 3)]
            dur = 3600 * dur[0] + 60 * dur[1] + dur[2]
            return dur

        root = ET.fromstring(self.content)
        pattern = r"^\{([\s\S]+)\}[\s\S]+$"  # namespace
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
            self._insert_adaptation_set(AdaptationSet(adapationSet, self))

    def get_adaptation_set(self, adaptation_set_id):
        return self.adaptationSets.get(adaptation_set_id)

    def _insert_adaptation_set(self, adaptation_set: AdaptationSet):
        self.adaptationSets[adaptation_set.id] = adaptation_set
