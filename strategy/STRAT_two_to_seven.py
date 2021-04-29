from strategy.__init__ import FTManager


class FTTwoSeven(FTManager):
    def get_state(self):
        states = {
            'get_asset' : {
                'state' : 0, 'time' : '090010'
            },
            'get_price' : {
                'state' : 1, 'time' : 'any'
            },
            'get_prediction' : {
                'state' : 2, 'time' : '090200'
            },
            'buy' : {
                'state' : 3, 'time' : '090200'
            },
            'sell' : {
                'state' : 4, 'time' : '090700'
            }
        }
        return states

    def my_name(self):
        return 'FTTwoSeven'
