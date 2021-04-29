from abc import ABC, abstractmethod


class FTManager(ABC):
    @abstractmethod
    def get_state(self):
        pass

    @abstractmethod
    def my_name(self):
        pass