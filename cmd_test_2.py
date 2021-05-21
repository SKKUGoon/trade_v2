from indice.INDEX_mavg import *

app = QApplication(sys.argv)
k = Kiwoom.instance()
k.connect()
order = {'index': True, 'option': False}
trd = MarketIndice(k, order)
app.exec()