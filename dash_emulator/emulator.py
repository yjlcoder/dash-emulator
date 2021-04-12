from abc import ABC, abstractmethod

import requests

from dash_emulator import mpd_parser


class Emulator(ABC):
    @abstractmethod
    async def start(self, mpd_url):
        pass


class EmulatorImpl(Emulator):
    def __init__(self):
        pass

    async def start(self, mpd_url):
        mpd_content: str = requests.get(mpd_url).text
        mpd_obj = mpd_parser.MPD(mpd_content, mpd_url)
