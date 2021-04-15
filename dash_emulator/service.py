from abc import abstractmethod, ABC


class AsyncService(ABC):
    @abstractmethod
    async def start(self):
        pass
