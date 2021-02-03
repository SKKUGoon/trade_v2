state = {
    # Morning Trade Start
    'Get_OMS_Asset': 0,
    'Compare_CO_Asset': 1,  # OMS Asset Code Acquired. Ready to Compare
    'Get_OMS_Live_Price': 2,  # OMS C-O Comparison Done. Ready for Live Price
    'Get_CMS_Live_Price1': 3,  # OMS Live Price Complete. Ready for Purchase
    'CMS_Sell': 4,  # CMS Live Price Complete. Ready for Selling
    'OMS_Buy': 5,  # CMS 1st Selling Complete. Ready for Checking Unexecuted Quantity.

    # Transaction Checking begins
    'CMS_Sell_Check': 6,  # OMS 1st Purchase Complete. Ready for Checking Unexecuted Quantity
    'OMS_Buy_Check': 6,

    # Conventional Morning Routine, 090000 ~ 090100
    'CMS_Sell_Done': 8,  # Still checking OMS_BUY
    'OMS_Buy_Done': 9,  # Still checking CMS_SELL
    'CMS_Sell_OMS_Buy_Done': 10,  # Both are done.

    # Conventional Morning Routine, 090700 ~
    'OMS_Sell': 11,
    'OMS_Sell_Check': 12,  # OMS Selling Complete.
    'OMS_Sell_Done': 13,

    # Morning Trade Over
    'Rest' : 14,
    # Evening Trade Start
    'Get_CMS_Asset': 15,
    'Get_CMS_Live_Price2': 16,  # CMS Asset Code Acquired. Ready for Live Price
    'CMS_Buy': 17,  # CMS Live Price Complete. Ready for Purchase
    'Trade_Finish': 18,  # CMS Purchase Complete. (Cannot buy unexecuted Quantity)
}

state2 = {
    # Morning Trade Start
    'Input_Models': 0,
    'Get_OMS_Asset': 101,
    'Get_CMS1_Asset': 102,
    'Compare_CO_Asset': 103,

    'CO_Same_Live_Price': 200 + True,
    'CO_Diff_OMS_Live_Price': 200 + False,

    'CO_Diff_CMS1_Live_Price': 300 + False,

    'CO_Same_CMS_Sell': 400 + True,
    'CO_Diff_CMS_Sell': 400 + False,

    'CO_Same_OMS_Buy': 500 + True,
    'CO_Diff_OMS_Buy': 500 + False,

    'CO_Same_OMS_Check': 600 + True,
    'CO_Diff_OMS_Check': 600 + False,

    'CO_Same_CMS_Check': 600 + True,
    'CO_Diff_CMS_Check': 600 + False,

    'CO_Same_OMS_Buy_Done': 700 + True,
    'CO_Diff_OMS_Buy_Done': 700 + False,

    'CO_Same_CMS_Sell_Done': 800 + True,
    'CO_Diff_OMS_Sell_Done': 800 + False,

    'OMS_Sell': 9,
    'OMS_Sell_Check': 10,  # OMS Selling Complete.
    'OMS_Sell_Done': 11,

    'Rest' : 12,
    'Get_CMS2_Asset': 13,
    'CMS_Buy': 14,  # CMS Live Price Complete. Ready for Purchase
    'Trade_Finish': 15,  # CMS Purchase Complete.
}

individual = {
    'get_asset_buy': 0,
    'get_rt_prc': 1,
    'send_main_thread': 2,
    'buy_asset': 3,
    'buy_complete': 4,
    'sell_asset': 5,
    'sell_complete': 6,
}