from _util.errors import *
from _util._log import *

from collections import deque
import datetime
import time



class RequestCheck:
    def __init__(self, logging:Logger):
        """
        5 req / 1 sec
        1000 req / 1 hr
        """
        self.req_q = deque(maxlen=1000)  # Record time here
        if logging is None:
            raise LoggerConnectionError("Logger Not Connected")
        else:
            self.log = logging
        ...

    def req_check(self):
        time.sleep(0.1)  #


        if len(self.req_q) < 5:
            pass
        else:
            self.__second_check()

        if len(self.req_q) == 1000:
            delay = self.__hour_check()
            start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            self.log.warning(
                f"{start}: Alert from RequestCheck. Request delayed by {delay} seconds"
            )
            time.sleep(delay)

        self.req_q.append(time.time())
        ...

    def __second_check(self):
        sec_limit = self.req_q[-4]

        while True:
            if abs(time.time() - sec_limit) > 1:
                break

    def __hour_check(self):
        hr_limit = self.req_q[0]
        t = time.time() - hr_limit
        if t < 3610:  # Request over 1000 in 3610s
            delay = 3610 - t
        return t


req_q = [1, 2, 3, 4, 5]