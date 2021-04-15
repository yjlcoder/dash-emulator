#!/usr/bin/env python3

import argparse
import asyncio
import logging
import pathlib
import re
import sys
from typing import Dict, Union

from dash_emulator.player_factory import build_dash_player

log = logging.getLogger(__name__)

PLAYER_TARGET = "target"


def create_parser():
    arg_parser = argparse.ArgumentParser(description="Accept for the emulator")
    # Add here

    arg_parser.add_argument("--proxy", type=str, help='NOT IMPLEMENTED YET')
    arg_parser.add_argument("--output", type=str, required=False, default=None,
                            help="Path to output folder. Indicate this argument to save videos and related data.")
    arg_parser.add_argument("--plot", required=False, default=False, action='store_true')
    arg_parser.add_argument("-y", required=False, default=False, action='store_true',
                            help="Automatically overwrite output folder")
    arg_parser.add_argument(PLAYER_TARGET, type=str, help="Target MPD file link")
    return arg_parser


def validate_args(arguments: Dict[str, Union[int, str, None]]) -> bool:
    # Validate target
    # args.PLAYER_TARGET is required
    if "target" not in arguments:
        log.error("Argument \"%s\" is required" % PLAYER_TARGET)
        return False
    # HTTP or HTTPS protocol
    results = re.match("^(http|https)://", arguments[PLAYER_TARGET])
    if results is None:
        log.error("Argument \"%s\" (%s) is not in the right format" % (
            PLAYER_TARGET, arguments[PLAYER_TARGET]))
        return False

    # Validate proxy
    # TODO

    # Validate Output
    if arguments["output"] is not None:
        path = pathlib.Path(arguments['output'])
        path.mkdir(parents=True, exist_ok=True)

    return True


if __name__ == '__main__':
    try:
        assert sys.version_info.major >= 3 and sys.version_info.minor >= 3
    except AssertionError:
        print("Python 3.3+ is required.")
        exit(-1)
    parser = create_parser()
    args = parser.parse_args()

    args = vars(args)

    validated = validate_args(args)

    if not validated:
        log.error("Arguments validation error, exit.")
        exit(-1)

    logging.basicConfig(level=logging.INFO)

    player = build_dash_player()

    asyncio.run(player.start(args["target"]))
