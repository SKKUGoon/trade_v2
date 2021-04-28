from typing import Dict

class TradeState:

    def __init__(self):
        self.states = {0 : 'Trade_Start'}
        self.strategy_add = 0

    def __repr__(self):
        return f'{self.strategy_add} strats added.'

    def add_strategy(self, strategy_name:str, buy:bool=True, sell:bool=True):
        """
        Additional strategy calls for additional trade state.
        One strategy requires
            1. Getting Asset
            2. Getting Live Price of that Asset
            3. Buying an Asset(Optional)
            4. Selling an Asset

        """
        addition = {
            1 : f'{strategy_name}_get_asset',
            2 : f'{strategy_name}_get_price',
            3 : f'{strategy_name}_buy_asset',
            4 : f'{strategy_name}_sell_asset',
        }

        # Create New state
        start_from = max(self.states.keys())
        for add, n in addition.items():
            if buy is False:
                if add == 3:
                    continue
            if sell is False:
                if add == 4:
                    continue
            self.states[(start_from + add)] = n

        self.strategy_add += 1

    def change_order(self, order_pairs:Dict):
        """
        ex)
        order_pair = {2 : 4}
        original value of key 2 will be assigned to key 4
        value of key 4 will be assigned to key 2
        """
        for k, v in order_pairs.items():
            if (k not in self.states.keys()) or (v not in self.states.keys()):
                raise KeyError(f'{k}, {v} not in {self.states.keys()}')

            from_ = self.states[k]
            to_ = self.states[v]

            self.states[v] = from_
            self.states[k] = to_
