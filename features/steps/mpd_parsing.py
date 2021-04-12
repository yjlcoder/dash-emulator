from inspect import cleandoc
from xml.etree import ElementTree

from behave import *

from dash_emulator.models.mpd_objects import MPD
from dash_emulator.mpd_parser import MPDParser, DefaultMPDParser

use_step_matcher("re")


@given("We have the MPD file content")
def step_impl(context):
    context.mpd_content = cleandoc(mpd_content_using_segment_template)
    context.url = "http://127.0.0.1/videos/BBB/output.mpd"


@when("nothing")
def step_impl(context):
    pass


@then("The MPD gets parsed right")
def step_impl(context):
    mpd_parser: MPDParser = DefaultMPDParser()
    mpd_obj: MPD = mpd_parser.parse(context.mpd_content, context.url)
    assert len(mpd_obj.adaptation_sets) == 1
    assert mpd_obj.media_presentation_duration == 19.9
    assert mpd_obj.max_segment_duration == 1.0
    assert mpd_obj.min_buffer_time == 2.0
    assert mpd_obj.type == "static"
    assert mpd_obj.url == context.url


@given("We have the XML tree of an AdaptationSet")
def step_impl(context):
    tree = ElementTree.fromstring(adaptation_content_using_segment_template)
    context.tree = tree
    context.url = "http://127.0.0.1/videos/BBB/"


@then("The AdaptationSet gets parsed right")
def step_impl(context):
    mpd_parser = DefaultMPDParser()
    adaptation_set = mpd_parser.parse_adaptation_set(context.tree, context.url)
    assert adaptation_set.id == 0
    assert adaptation_set.content_type == "video"
    assert adaptation_set.max_width == 1920
    assert adaptation_set.max_height == 1080
    assert adaptation_set.frame_rate == "30/1"
    assert adaptation_set.par == "16:9"
    assert len(adaptation_set.representations) == 7
    assert adaptation_set.representations.get(0).bandwidth == 2446879
    assert adaptation_set.representations.get(6).bandwidth == 202066


@given("We have the XML tree of a representation")
def step_impl(context):
    tree = ElementTree.fromstring(representation_content_using_segment_template)
    context.tree = tree
    context.url = "http://127.0.0.1/videos/BBB/"


@then("The Representation gets parsed right")
def step_impl(context):
    mpd_parser = DefaultMPDParser()
    representation = mpd_parser.parse_representation(context.tree, context.url)
    assert representation.id == 0
    assert representation.mime_type == "video/mp4"
    assert representation.codecs == "av01.0.08M.08"
    assert representation.bandwidth == 2446879
    assert representation.width == 1920
    assert representation.height == 1080
    assert len(representation.segments) == 19
    assert representation.initialization == "http://127.0.0.1/videos/BBB/init-stream0.m4s"
    assert representation.segments[0].url == "http://127.0.0.1/videos/BBB/chunk-stream0-00001.m4s"
    assert representation.segments[0].duration == 1.0
    assert representation.segments[18].url == "http://127.0.0.1/videos/BBB/chunk-stream0-00019.m4s"
    assert representation.segments[18].duration == 29.0 / 30


mpd_content_using_segment_template = """
    <?xml version="1.0" encoding="utf-8"?>
    <MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns="urn:mpeg:dash:schema:mpd:2011"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xsi:schemaLocation="urn:mpeg:DASH:schema:MPD:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd"
        profiles="urn:mpeg:dash:profile:isoff-live:2011"
        type="static"
        mediaPresentationDuration="PT19.9S"
        maxSegmentDuration="PT1.0S"
        minBufferTime="PT2.0S">
        <ProgramInformation>
        </ProgramInformation>
        <ServiceDescription id="0">
        </ServiceDescription>
        <Period id="0" start="PT0.0S">
            <AdaptationSet id="0" contentType="video" startWithSAP="1" segmentAlignment="true" bitstreamSwitching="true" frameRate="30/1" maxWidth="1920" maxHeight="1080" par="16:9" lang="und">
                <Representation id="0" mimeType="video/mp4" codecs="av01.0.08M.08" bandwidth="2446879" width="1920" height="1080" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="1" mimeType="video/mp4" codecs="av01.0.08M.08" bandwidth="1628084" width="1920" height="1080" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="2" mimeType="video/mp4" codecs="av01.0.05M.08" bandwidth="1104415" width="1280" height="720" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="3" mimeType="video/mp4" codecs="av01.0.05M.08" bandwidth="737899" width="1280" height="720" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="4" mimeType="video/mp4" codecs="av01.0.04M.08" bandwidth="487224" width="1024" height="576" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="5" mimeType="video/mp4" codecs="av01.0.01M.08" bandwidth="321163" width="640" height="360" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
                <Representation id="6" mimeType="video/mp4" codecs="av01.0.00M.08" bandwidth="202066" width="426" height="240" scanType="unknown" sar="1:1">
                    <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                        <SegmentTimeline>
                            <S t="0" d="30000" r="18" />
                            <S d="29000" />
                        </SegmentTimeline>
                    </SegmentTemplate>
                </Representation>
            </AdaptationSet>
        </Period>
    </MPD>
    """

representation_content_using_segment_template = """
            <Representation id="0" mimeType="video/mp4" codecs="av01.0.08M.08" bandwidth="2446879" width="1920" height="1080" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
"""

adaptation_content_using_segment_template = """
        <AdaptationSet id="0" contentType="video" startWithSAP="1" segmentAlignment="true" bitstreamSwitching="true" frameRate="30/1" maxWidth="1920" maxHeight="1080" par="16:9" lang="und">
            <Representation id="0" mimeType="video/mp4" codecs="av01.0.08M.08" bandwidth="2446879" width="1920" height="1080" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="1" mimeType="video/mp4" codecs="av01.0.08M.08" bandwidth="1628084" width="1920" height="1080" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="2" mimeType="video/mp4" codecs="av01.0.05M.08" bandwidth="1104415" width="1280" height="720" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="3" mimeType="video/mp4" codecs="av01.0.05M.08" bandwidth="737899" width="1280" height="720" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="4" mimeType="video/mp4" codecs="av01.0.04M.08" bandwidth="487224" width="1024" height="576" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="5" mimeType="video/mp4" codecs="av01.0.01M.08" bandwidth="321163" width="640" height="360" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
            <Representation id="6" mimeType="video/mp4" codecs="av01.0.00M.08" bandwidth="202066" width="426" height="240" scanType="unknown" sar="1:1">
                <SegmentTemplate timescale="30000" initialization="init-stream$RepresentationID$.m4s" media="chunk-stream$RepresentationID$-$Number%05d$.m4s" startNumber="1">
                    <SegmentTimeline>
                        <S t="0" d="30000" r="18" />
                        <S d="29000" />
                    </SegmentTimeline>
                </SegmentTemplate>
            </Representation>
        </AdaptationSet>

"""
