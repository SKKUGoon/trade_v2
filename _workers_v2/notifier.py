from PyQt5.QtCore import *
from _util.chat_assist import LineNotifier

from queue import Queue

class Notifier(QThread):
    def __init__(self, queue:Queue):
        super().__init__()
        self.m = LineNotifier()
        self.in_queue = queue

    @pyqtSlot()
    def run(self):
        while True:
            if not self.in_queue.empty():
                msg = self.in_queue.get(block=False)
                self.m.post_message(msg)
            else:
                self.sleep(2)