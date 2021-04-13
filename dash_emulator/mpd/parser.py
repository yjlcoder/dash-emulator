import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from dash_emulator.models import MPD, AdaptationSet, Representation, Segment


class MPDParsingException(Exception):
    pass


class MPDParser(ABC):
    @abstractmethod
    def parse(self, content: str, url: str) -> MPD:
        pass


class DefaultMPDParser(MPDParser):
    log = logging.getLogger("DefaultMPDParser")

    @staticmethod
    def parse_iso8601_time(duration) -> float:
        """
        Parse the ISO8601 time string to the number of seconds
        """
        pattern = r"^PT(?:(\d+(?:.\d+)?)H)?(?:(\d+(?:.\d+)?)M)?(?:(\d+(?:.\d+)?)S)?$"
        results = re.match(pattern, duration)
        dur = [float(i) if i is not None else 0 for i in results.group(1, 2, 3)]
        dur = 3600 * dur[0] + 60 * dur[1] + dur[2]
        return dur

    @staticmethod
    def remove_namespace_from_content(content):
        """
        Remove the namespace string from XML string
        """
        content = re.sub('xmlns="[^"]+"', '', content, count=1)
        return content

    def parse(self, content: str, url: str) -> MPD:
        content = self.remove_namespace_from_content(content)
        root = ElementTree.fromstring(content)

        # type
        type_ = root.attrib["type"]

        # media presentation duration
        media_presentation_duration = self.parse_iso8601_time(root.attrib.get("mediaPresentationDuration", ""))

        # min buffer duration
        min_buffer_time = self.parse_iso8601_time(root.attrib.get("minBufferTime", ""))

        # max segment duration
        max_segment_duration = self.parse_iso8601_time(root.attrib.get("maxSegmentDuration", ""))

        period = root.find("Period")

        if period is None:
            error_msg = """Cannot find "Period" tag"""
            self.log.error(error_msg)
            raise MPDParsingException(error_msg)

        adaptation_sets: Dict[int, AdaptationSet] = {}

        base_url = os.path.dirname(url) + '/'

        for adaptation_set_xml in period:
            adaptation_set: AdaptationSet = self.parse_adaptation_set(adaptation_set_xml, base_url)
            adaptation_sets[adaptation_set.id] = adaptation_set

        return MPD(content, url, type_, media_presentation_duration, max_segment_duration, min_buffer_time,
                   adaptation_sets)

    def parse_adaptation_set(self, tree: Element, base_url) -> AdaptationSet:
        id_ = tree.attrib.get("id")
        content_type = tree.attrib.get("contentType")
        frame_rate = tree.attrib.get("frameRate")
        max_width = int(tree.attrib.get("maxWidth"))
        max_height = int(tree.attrib.get("maxHeight"))
        par = tree.attrib.get("par")

        representations = {}
        for representation_tree in tree:
            representation = self.parse_representation(representation_tree, base_url)
            representations[representation.id] = representation
        return AdaptationSet(int(id_), content_type, frame_rate, max_width, max_height, par, representations)

    def parse_representation(self, tree: Element, base_url) -> Representation:
        segment_template = tree.find("SegmentTemplate")
        if segment_template is not None:
            return self.parse_representation_with_segment_template(tree, base_url)
        else:
            raise MPDParsingException("The MPD support is not complete yet")

    @staticmethod
    def parse_representation_with_segment_template(tree: Element, base_url) -> Representation:
        id_ = tree.attrib['id']
        mime = tree.attrib['mimeType']
        codec = tree.attrib['codecs']
        bandwidth = int(tree.attrib['bandwidth'])
        width = int(tree.attrib['width'])
        height = int(tree.attrib['height'])

        segment_template: Element = tree.find("SegmentTemplate")
        initialization = segment_template.attrib.get("initialization").replace("$RepresentationID$", id_)
        initialization = base_url + initialization
        segments: List[Segment] = []

        timescale = int(segment_template.attrib.get("timescale"))
        media = segment_template.attrib.get("media").replace("$RepresentationID$", id_)
        start_number = int(segment_template.attrib.get('startNumber'))

        segment_timeline = segment_template.find("SegmentTimeline")

        num = start_number
        for segment in segment_timeline:  # type: Element
            duration = float(segment.attrib.get("d")) / timescale
            url = base_url + re.sub(r"\$Number(%\d+d)\$", r"\1", media) % num
            segments.append(Segment(url, duration))
            num += 1

            if 'r' in segment.attrib:  # repeat
                for i in range(1, int(segment.attrib.get('r'))):
                    url = base_url + re.sub(r"\$Number(%\d+d)\$", r"\1", media) % num
                    segments.append(Segment(url, duration))
                    num += 1
        return Representation(int(id_), mime, codec, bandwidth, width, height, initialization, segments)
