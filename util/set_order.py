def order_base(name, scr_num, account, asset, buy_sell, trade_type, quantity, price, order_num=""):
    order = {
        'rq_name': name,
        'screen_num': scr_num,
        'account': account,
        'code': asset,
        'order_type': 1,
        'buy_sell': buy_sell,
        'trade_type': trade_type,
        'quantity': quantity,
        'price': price,
        'order_num': order_num
    }
    return order



class OrderSheet:
    def __init__(self):
        pass

    def order_base(self, name, ):
        order = {
            'rq_name': '',
            'screen_num': '',
            'account': '',
            'code': '',
            'order_type': 1,  # 1: New, 2: Refract, 3: Cancel
            'buy_sell': '',  # Selling: 1, Buying: 2
            'trade_type': 1,  # Designated Price
            'quantity': '',
            'price': '',
            'order_num': "",
        }
        return order

    @staticmethod
    def get_quantity(total_value, price):
        return total_value // (price * 250000)

    @staticmethod
    def set_adjust_price(original_price, tick):
        if original_price >= 10:
            base = 0.5
            return original_price + base * tick
        else:
            base = 0.1
            return original_price + base * tick

    @staticmethod
    def chk_premium(price:float, decimal=2, standard=5):
        if price >= 10:
            if price * (10 ** (decimal)) % 5 == 0:
                return price
            else:
                price_d = price * (10 ** decimal)
                return (price_d + (standard - (price_d % standard))) * 10 ** (-decimal)
        else:
            return price

    @staticmethod
    def _floor(value, decimal=2):
        return (value * (10 ** decimal) // 1) * (10 ** - decimal)