#!/usr/bin/env python3

import argparse
import asyncio
import pathlib
import re
import sys
from typing import Dict, Union

from dash_emulator import logger, arguments, emulator

log = logger.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser(description="Accept arguments for the emulator")
    # Add arguments here

    parser.add_argument("--proxy", type=str, help='NOT IMPLEMENTED YET')
    parser.add_argument("--output", type=str, required=False, default=None,
                        help="Path to output folder. Indicate this argument to save videos and related data.")
    parser.add_argument("--plot", required=False, default=False, action='store_true')
    parser.add_argument("-y", required=False, default=False, action='store_true',
                        help="Automatically overwrite output folder")
    parser.add_argument(arguments.PLAYER_TARGET, type=str, help="Target MPD file link")
    return parser


def validate_args(args: Dict[str, Union[int, str, None]]) -> bool:
    # Validate target
    # args.PLAYER_TARGET is required
    if "target" not in args:
        log.error("Argument \"%s\" is required" % arguments.PLAYER_TARGET)
        return False
    # HTTP or HTTPS protocol
    results = re.match("^(http|https)://", args[arguments.PLAYER_TARGET])
    if results is None:
        log.error("Argument \"%s\" (%s) is not in the right format" % (
            arguments.PLAYER_TARGET, args[arguments.PLAYER_TARGET]))
        return False

    # Validate proxy
    # TODO

    # Validate Output
    if args["output"] is not None:
        path = pathlib.Path(args['output'])
        path.mkdir(parents=True, exist_ok=True)

    return True


if __name__ == '__main__':
    try:
        assert sys.version_info.major >= 3 and sys.version_info.minor >= 3
    except AssertionError:
        print("Python 3.3+ is required.")
        exit(-1)
    logger.config()
    parser = create_parser()
    args = parser.parse_args()

    args = vars(args)

    validated = validate_args(args)

    if not validated:
        log.error("Arguments validation error, exit.")
        exit(-1)

    emulator = emulator.Emulator(args)

    try:
        # Python 3.7+
        asyncio.run(emulator.start())
    except AttributeError:
        # Lower than Python 3.7
        loop = asyncio.get_event_loop()
        loop.run_until_complete(emulator.start())
