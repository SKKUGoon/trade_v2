from strategy.STRAT_two_to_seven import *
from strategy.STRAT_cms import *
from strategy.STRAT_cms_ext import *


class FTFactory:
    def timing(self, strat):
        return strat.get_state()

    def naming(self, strat):
        return strat.my_name()


if __name__ == '__main__':
    d = FTFactory()
    print(d.timing(FTTwoSeven()))
    print(d.timing(FTCMS()))
    print(d.timing(FTCMSExt()))