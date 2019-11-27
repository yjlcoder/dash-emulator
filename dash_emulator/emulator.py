import requests

from dash_emulator import arguments, mpd


class Emulator():
    def __init__(self, args):
        self.args = args
        self.mpd = None

    def start(self):
        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)
