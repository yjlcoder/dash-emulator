import requests

from dash_emulator import arguments


class Emulator():
    def __init__(self, args):
        self.args = args

    def MPD_parser(self, content):
        pass

    def start(self):
        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
