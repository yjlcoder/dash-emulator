import asyncio
import inspect
from typing import Callable, List, Union, Optional

from dash_emulator import logger

log = logger.getLogger(__name__)


class Event(object):
    @staticmethod
    async def trigger(*args, **kwargs):
        await EventBridge().trigger(__class__, *args, **kwargs)

    def __init__(self):
        self.callbacks = []  # type: List[Callable]

    async def trigger(self, *args, **kwargs):
        for callback in self.callbacks:
            try:
                # Python 3.7
                asyncio.create_task(callback(*args, **kwargs))
            except AttributeError:
                # Lower than Python 3.7
                loop = asyncio.get_event_loop()
                loop.create_task(callback(*args, **kwargs))


class Events(object):
    class DownloadEnd(Event):
        """
        Event triggered when downloading has end, but the playback is not over
        """
        pass

    class MPDParseComplete(Event):
        """
        Event triggered when MPD file get parsed
        """
        pass

    class CanPlay(Event):
        """
        Event triggered when the buffer level >= minBufferLevel indicated in MPD file
        """
        pass

    class Stall(Event):
        """
        Event triggered when the player is waiting for a new segment
        """
        pass

    class DownloadComplete(Event):
        """
        Event triggered when a segment is downloaded completely
        """
        pass

    class SegmentDownloadComplete(Event):
        """
        Event triggered when all the adaptation sets for a segment are downloaded
        """

    class InitializationDownloadComplete(Event):
        """
        Event triggered when the init file is downloaded completely
        For each stream, the init file is required to download before the segment file
        To get a playable segment, concatenate init file and the segment file (normally m4s)
        `cat stream0-init.mp4 stream0-segment3.m4s > stream0-segment4.mp4`
        """
        pass

    class DownloadStart(Event):
        """
        Event triggered when the download starts
        """
        pass

    class Play(Event):
        """
        Event triggered when the player starts playing
        """
        pass

    class End(Event):
        """
        Event triggered when the playback is over
        """
        pass

    class BufferUpdated(Event):
        pass


class EventBridge():
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

            # __init__ is running out of the event loop. You cannot create Queue() here.
            self._queue = None  # type: Optional[asyncio.Queue]
            self.loop = None  # type: Optional[asyncio.BaseEventLoop]

            self.over = False

    def add_listener(self, event: Union[str, Event, Event.__class__], callback: Callable):
        if isinstance(event, str):
            self.add_listener(self._dic_name_obj[event], callback)
            return
        if inspect.isclass(event) and issubclass(event, Event):
            self.add_listener(self._dic_name_obj[event.__name__], callback)
            return
        event.callbacks.append(callback)

    async def trigger(self, event: Union[str, Event, Event.__class__], *args, **kwargs):
        if isinstance(event, str):
            log.debug("Event %s is triggered." % str(type(event)))
            await self.trigger(self._dic_name_obj[event], *args, **kwargs)
            return
        if inspect.isclass(event) and issubclass(event, Event):
            log.debug("Event %s is triggered." % event)
            await self.trigger(self._dic_name_obj[event.__name__], *args, **kwargs)
            return
        # self.loop.call_soon_threadsafe(lambda x: self.loop.create_task(self._queue.put(x)), event)
        self.loop.create_task(self._queue.put((event, args, kwargs)))

    async def listen(self):
        while not self.over or not self._queue.empty():
            args = None,
            kwargs = None
            try:
                event, args, kwargs = await asyncio.wait_for(self._queue.get(), 1)
            except asyncio.TimeoutError:
                continue
            log.info("Event %s got triggered" % event.__class__.__name__)
            await event.trigger(*args, **kwargs)

    # def run(self):
    #     self.loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(self.loop)
    #     self._queue = asyncio.Queue()
    #
    #     self.loop.run_until_complete(self.listen())

    async def init_queue(self):
        self.loop = asyncio.get_event_loop()
        self._queue = asyncio.Queue(loop=self.loop)
