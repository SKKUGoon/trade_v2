def order_base(name, scr_num, account, asset, buy_sell, trade_type, quantity, price,
               order_type=1, order_num=""):
    order = {
        'rq_name': name,
        'screen_num': scr_num,
        'account': account,
        'code': asset,
        'order_type': order_type,
        'buy_sell': buy_sell,
        'trade_type': trade_type,
        'quantity': quantity,
        'price': price,
        'order_num': order_num
    }
    return order