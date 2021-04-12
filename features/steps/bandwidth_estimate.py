import asyncio
from types import SimpleNamespace

from behave import *

from dash_emulator.bandwidth import BandwidthMeterImpl, BandwidthUpdateListener

use_step_matcher("re")


@given("We have a default bandwidth meter")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """

    class MockBandwidthUpdateListener(BandwidthUpdateListener):
        def __init__(self):
            self.updated = False

        async def on_bandwidth_update(self, bw: int) -> None:
            print("Bandwidth updated: %d" % bw)
            self.updated = True

    context.args = SimpleNamespace()
    context.args.listener = MockBandwidthUpdateListener()
    context.args.bandwidth_meter = BandwidthMeterImpl(1000, 0.5, [context.args.listener])


@when("The transmission complete")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    bandwidth_meter: BandwidthMeterImpl = context.args.bandwidth_meter
    url = "http://foo.bar"

    async def feed():
        await bandwidth_meter.on_transfer_start("http://foo.bar")
        await asyncio.sleep(0.1)
        await bandwidth_meter.on_bytes_transferred(500, url, 500, 1000)
        await asyncio.sleep(0.1)
        await bandwidth_meter.on_bytes_transferred(500, url, 1000, 1000)
        await bandwidth_meter.on_transfer_end(1000, url)

    asyncio.run(feed())


@then("the bandwidth should be estimated correctly")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    bandwidth_meter: BandwidthMeterImpl = context.args.bandwidth_meter
    print(bandwidth_meter.bandwidth)
    assert abs(bandwidth_meter.bandwidth - 40000) < 1000


@then("the listener should be triggered")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    assert context.args.listener.updated is True


@when("the transmission hasn't started")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    pass


@then("The bandwidth should be initial bandwidth")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    bandwidth_meter: BandwidthMeterImpl = context.args.bandwidth_meter
    assert bandwidth_meter.bandwidth == 1000


@when("The two transmissions complete")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    bandwidth_meter: BandwidthMeterImpl = context.args.bandwidth_meter
    url = "http://foo.bar"

    async def feed():
        await bandwidth_meter.on_transfer_start("http://foo.bar")
        await asyncio.sleep(0.1)
        await bandwidth_meter.on_bytes_transferred(500, url, 500, 1000)
        await asyncio.sleep(0.1)
        await bandwidth_meter.on_bytes_transferred(500, url, 1000, 1000)
        await bandwidth_meter.on_transfer_end(1000, url)

        await bandwidth_meter.on_transfer_start("http://foo.bar")
        await asyncio.sleep(0.05)
        await bandwidth_meter.on_bytes_transferred(500, url, 500, 1000)
        await asyncio.sleep(0.05)
        await bandwidth_meter.on_bytes_transferred(500, url, 1000, 1000)
        await bandwidth_meter.on_transfer_end(1000, url)

    asyncio.run(feed())


@then("The bandwidth should be estimated correctly for 2 transmissions")
def step_impl(context):
    """
    Parameters
    ----------
    context : behave.runner.Context
    """
    bandwidth_meter: BandwidthMeterImpl = context.args.bandwidth_meter
    assert abs(bandwidth_meter.bandwidth - 60000) < 1000
