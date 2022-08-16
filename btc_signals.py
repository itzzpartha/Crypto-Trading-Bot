# total trades
# winning trades, losing trades, win:loss ratio
# max winning streak, max losing streak
# total % gain

import redis
from binance.client import Client
from binance.enums import *

api_key = '' # client api key
api_secret = '' # client api secret
client = Client(api_key=api_key, api_secret=api_secret, testnet=False)

redisConnPool0 = redis.ConnectionPool(host='10.68.131.59', port=6379, db=0)
redisClient0 = redis.Redis(connection_pool=redisConnPool0)

maxLoss = 5
        
while True:
    Current_Trade = int(redisClient0.get("Current_Trade"))
    ltp = float(redisClient0.get("LTP"))
    if Current_Trade == 0:
        Bullish_Above = float(redisClient0.get("Bullish_Above"))
        Bearish_Below = float(redisClient0.get("Bearish_Below"))
        if (ltp > Bullish_Above)&((ltp-Bullish_Above) < 0.001*ltp):
            SH = float(redisClient0.get("Swing_High"))
            SL = float(redisClient0.get("Swing_Low"))
            print("Long Signal")
            quantity = round(maxLoss/(SH-SL),3)
            redisClient0.set("quantity",quantity)
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='BUY',quantity=quantity)
            redisClient0.set("Current_Trade",1)
            redisClient0.set("Target",Bullish_Above + SH - SL)
            redisClient0.set("StopLoss",SL)
        elif (ltp < Bearish_Below)&((Bearish_Below-ltp)<0.001*ltp):
            SH = float(redisClient0.get("Swing_High"))
            SL = float(redisClient0.get("Swing_Low"))
            print("Short Signal")
            quantity = round(maxLoss/(SH-SL),3)
            redisClient0.set("quantity",quantity)
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='SELL',quantity=quantity)
            redisClient0.set("Current_Trade",-1)
            redisClient0.set("Target",Bearish_Below - SH + SL)
            redisClient0.set("StopLoss",SH)
    elif Current_Trade == 1:
        ltp_h = float(redisClient0.get("LTP_H"))
        StopLoss = float(redisClient0.get("StopLoss"))
        Target = float(redisClient0.get("Target"))
        quantity = float(redisClient0.get("quantity"))
        if ltp_h > Target:
            print("Square Off Long")
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='SELL',quantity=quantity)
            redisClient0.set("Current_Trade",0)
            redisClient0.set("Bullish_Above",ltp*2)
        elif ltp < StopLoss:
            print("Square Off Long")
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='SELL',quantity=quantity)
            redisClient0.set("Current_Trade",0)
            redisClient0.set("Bullish_Above",ltp*2)
    elif Current_Trade == -1:
        ltp_l = float(redisClient0.get("LTP_L"))
        StopLoss = float(redisClient0.get("StopLoss"))
        Target = float(redisClient0.get("Target"))
        quantity = float(redisClient0.get("quantity"))
        if ltp_l < Target:
            print("Square Off Short")
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='BUY',quantity=quantity)
            redisClient0.set("Current_Trade",0)
            redisClient0.set("Bearish_Below",0)
        elif ltp > StopLoss:
            print("Square Off Short")
            client.futures_create_order(symbol='BTCUSDT',type='MARKET',side='BUY',quantity=quantity)
            redisClient0.set("Current_Trade",0)
            redisClient0.set("Bearish_Below",0)
