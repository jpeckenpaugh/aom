import asyncio
import os
import sys

import pygame  # Keep visible to Pygbag's entrypoint dependency scanner.


def apply_native_resolution_arg(args):
    for arg in args:
        if arg.startswith("resolution="):
            os.environ["AOM_NATIVE_RESOLUTION"] = arg.split("=", 1)[1]
        elif arg.startswith("--resolution="):
            os.environ["AOM_NATIVE_RESOLUTION"] = arg.split("=", 1)[1]


apply_native_resolution_arg(sys.argv[1:])

from game import Game


if __name__ == "__main__":
    asyncio.run(Game().run_async())
