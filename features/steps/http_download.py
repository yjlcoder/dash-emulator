import asyncio
from types import SimpleNamespace

from behave import *

from dash_emulator.download import DownloadManagerImpl, DownloadEventListener

use_step_matcher("re")


@given("We have an HTTP download manager")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """

    class ProgressListener(DownloadEventListener):
        def __init__(self):
            self.on_download_complete_triggered = False
            self.on_bytes_downloaded_triggered = False
            self.on_transfer_start_triggered = False

        async def on_transfer_start(self, url) -> None:
            print("Download Start, url: " + url)
            self.on_transfer_start_triggered = True

        async def on_transfer_end(self, size: int, url: str) -> None:
            print("Download Complete. Size: %10d" % size)
            self.on_download_complete_triggered = True

        async def on_bytes_transferred(self, length: int, url: str, position: int, size: int) -> None:
            print("%10d, %10d/%10d" % (length, position, size))
            self.on_bytes_downloaded_triggered = True

        async def on_transfer_canceled(self, url: str, position: int, size: int) -> None:
            print("Transfer canceled")

    context.args = SimpleNamespace()
    context.args.listener = ProgressListener()
    context.args.download_manager = DownloadManagerImpl([context.args.listener], False, 1024)


@when("The HTTP download manager starts to download Google's Logo")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    context.args.url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"


@then("It is downloaded and also called listeners")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """

    async def run():
        assert context.args.download_manager.is_busy is False
        asyncio.set_event_loop(asyncio.new_event_loop())
        task = asyncio.create_task(context.args.download_manager.download(context.args.url))
        await asyncio.sleep(0.005)
        assert context.args.download_manager.is_busy is True
        await task
        await context.args.download_manager.close()
        assert context.args.listener.on_download_complete_triggered is True
        assert context.args.listener.on_bytes_downloaded_triggered is True
        assert context.args.listener.on_transfer_start_triggered is True
        assert context.args.download_manager.is_busy is False

    asyncio.run(run())
