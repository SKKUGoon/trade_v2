<h1> Auto Trading Program </h1>

This trading program uses kiwoom to trade.

1. code_ includes error message details, error code details etc. 
2. data includes data updating method to execute each fixed time strategy
3. indice deprecated
4. **main**
- KW ... : Base class(Kiwoom)
- KWDERIV ... : Derivatives of Kiwoom. live db conn controls live data, order spec controls not-live data, ording asset etc.
- TRADE : Actual trading process using both KWDERIV files.
5. models includes fixed time models(Double SVCs)
6. strategy includes parameters used for each strategy such as starting time, finish time. Use class factory
7. util includes utility program such as fpca, asset code(option code) generator, notifier(notify with line messenger), etc.
8. workers
- each strategy has separate threads assigned to it. each thread executes seperate order. 
- check whether asset(option) is already bought via dbms.py from util. 
- if the asset is already bought and next strategy requires it to buy it, it skips that process automatically.
