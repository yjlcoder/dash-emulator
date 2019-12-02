import asyncio
import inspect
import threading
from typing import Callable, List, Union, Optional

from dash_emulator import logger

log = logger.getLogger(__name__)


class Event(object):
    @staticmethod
    async def trigger():
        await EventBridge().trigger(__class__)

    def __init__(self):
        self.callbacks = []  # type: List[Callable]

    async def trigger(self):
        for callback in self.callbacks:
            try:
                # Python 3.7
                asyncio.create_task(callback())
            except AttributeError:
                # Lower than Python 3.7
                loop = asyncio.get_event_loop()
                loop.create_task(callback())


class Events(object):
    class MPDParseComplete(Event):
        pass

    class CanPlay(Event):
        pass

    class Stall(Event):
        pass

    class DownloadComplete(Event):
        pass

    class InitializationDownloadComplete(Event):
        pass

    class DownloadStart(Event):
        pass

    class Play(Event):
        pass

    class End(Event):
        pass


class EventBridge(threading.Thread):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            super().__init__()
            self.inited = True
            available_events = inspect.getmembers(Events, lambda x: inspect.isclass(x) and issubclass(x, Event))

            self._dic_name_obj = {}

            for name, cls in available_events:
                self._dic_name_obj[name] = cls()

            self._queue = None  # type: Optional[asyncio.Queue]
            self.loop = None  # type: Optional[asyncio.BaseEventLoop]

    def add_listener(self, event: Union[str, Event, Event.__class__], callback: Callable):
        if isinstance(event, str):
            self.add_listener(self._dic_name_obj[event], callback)
            return
        if inspect.isclass(event) and issubclass(event, Event):
            self.add_listener(self._dic_name_obj[event.__name__], callback)
            return
        event.callbacks.append(callback)

    async def trigger(self, event: Union[str, Event, Event.__class__]):
        if isinstance(event, str):
            await self.trigger(self._dic_name_obj[event])
            return
        if inspect.isclass(event) and issubclass(event, Event):
            await self.trigger(self._dic_name_obj[event.__name__])
            return
        self.loop.call_soon_threadsafe(lambda x: self.loop.create_task(self._queue.put(x)), event)

    async def listen(self):
        while True:
            event = await self._queue.get()
            log.debug("Event %s got triggered" % event.__class__.__name__)
            await event.trigger()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._queue = asyncio.Queue()

        self.loop.run_until_complete(self.listen())
