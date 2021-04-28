from abc import ABC, abstractmethod


class FTManager(ABC):
    @abstractmethod
    def get_time(self):
        pass