import inspect
from typing import Callable, List, Union


class Event(object):
    @staticmethod
    async def trigger():
        await EventBridge().trigger(__class__)

    def __init__(self):
        self.callbacks = []  # type: List[Callable]

    async def trigger(self):
        for callback in self.callbacks:
            await callback()


class Events(object):
    class MPDParseComplete(Event):
        pass

    class CanPlay(Event):
        pass

    class Stall(Event):
        pass

    class DownloadComplete(Event):
        pass

    class DownloadStart(Event):
        pass

    class Play(Event):
        pass

    class End(Event):
        pass


class EventBridge(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            self.inited = True
            available_events = inspect.getmembers(Events, lambda x: inspect.isclass(x) and issubclass(x, Event))

            self._dic_name_obj = {}

            for name, cls in available_events:
                self._dic_name_obj[name] = cls()

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
        await event.trigger()
