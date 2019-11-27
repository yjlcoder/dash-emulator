import argparse
import re
from typing import Dict, Union

from dash_emulator import logger, arguments, emulator

log = logger.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser(description="Accept arguments for the emulator")
    # Add arguments here

    parser.add_argument("--proxy", type=str)
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

    return True


if __name__ == '__main__':
    logger.config()
    parser = create_parser()
    args = parser.parse_args()

    args = args.__dict__

    validated = validate_args(args)

    if not validated:
        log.error("Arguments validation error, exit.")
        exit(-1)

    emulator = emulator.Emulator(args)
    emulator.start()
