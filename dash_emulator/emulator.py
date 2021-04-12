from abc import ABC, abstractmethod

import requests

from dash_emulator.models import MPD
from dash_emulator.mpd_parser import MPDParser


class Emulator(ABC):
    @abstractmethod
    async def start(self, mpd_url):
        pass


class EmulatorImpl(Emulator):
    def __init__(self, mpd_parser: MPDParser):
        self.mpd_parser = mpd_parser

    async def start(self, mpd_url):
        mpd_content: str = requests.get(mpd_url).text
        mpd: MPD = self.mpd_parser.parse(mpd_content, mpd_url)
