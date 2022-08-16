import websocket, json, redis

def generate_levels():
    SH = float(redisClient0.get("Swing_High"))
    SL = float(redisClient0.get("Swing_Low"))
    PSH = float(redisClient0.get("Previous_Swing_High"))
    PSL = float(redisClient0.get("Previous_Swing_Low"))
    Current_Trade = int(redisClient0.get("Current_Trade"))
    StopLoss = float(redisClient0.get("StopLoss"))
    if SH < PSH:
        redisClient0.set("Bullish_Above",SH)
    if SL > PSL:
        redisClient0.set("Bearish_Below",SL)
    if (Current_Trade == 1)&(SL > StopLoss):
        redisClient0.set("StopLoss",SL)
    elif (Current_Trade == -1)&(SH < StopLoss):
        redisClient0.set("StopLoss",SH)

def generate_signal(ws, message):
    flag = json.loads(message)["k"]["x"]
    if flag:
        HIGH = float(redisClient0.get("HIGH"))
        LOW = float(redisClient0.get("LOW"))
        H = float(json.loads(message)["k"]["h"])
        L = float(json.loads(message)["k"]["l"])
        if H > HIGH:
            redisClient0.set("HIGH",H)
            HIGH = H
            Last_Swing = int(redisClient0.get("Last_Swing"))
            if Last_Swing == -1:
                redisClient0.set("LOW",L)
            else:
                if (HIGH-LOW)>0.01*LOW:
                    redisClient0.set("Last_Swing",-1)
                    redisClient0.set("LOW",L)
                    redisClient0.set("Previous_Swing_Low",redisClient0.get("Swing_Low"))
                    redisClient0.set("Swing_Low",LOW)
                    # print("New Swing Low Detected")
                    generate_levels()
        if L < LOW:
            redisClient0.set("LOW",L)
            LOW = L
            Last_Swing = int(redisClient0.get("Last_Swing"))
            if Last_Swing == 1:
                redisClient0.set("HIGH",H)
            else:
                if (HIGH-LOW)>0.01*LOW:
                    redisClient0.set("Last_Swing",1)
                    redisClient0.set("HIGH",H)
                    redisClient0.set("Previous_Swing_High",redisClient0.get("Swing_High"))
                    redisClient0.set("Swing_High",HIGH)
                    # print("New Swing High Detected")
                    generate_levels()
    else:
        redisClient0.set("LTP",json.loads(message)["k"]["c"])
        redisClient0.set("LTP_H",json.loads(message)["k"]["h"])
        redisClient0.set("LTP_L",json.loads(message)["k"]["l"])
    
socket = 'wss://stream.binance.com:9443/ws/btcusdt@kline_1m'
redisConnPool0 = redis.ConnectionPool(host='10.68.131.59', port=6379, db=0)
redisClient0 = redis.Redis(connection_pool=redisConnPool0)

redisClient0.set("Swing_High",input("Enter Swing High : "))
redisClient0.set("Previous_Swing_High",input("Enter Previous Swing High : "))
redisClient0.set("Swing_Low",input("Enter Swing Low : "))
redisClient0.set("Previous_Swing_Low",input("Enter Previous Swing Low : "))
redisClient0.set("Current_Trade",0)
redisClient0.set("StopLoss",0)
redisClient0.set("Target",0)
redisClient0.set("Bullish_Above",10000000)
redisClient0.set("Bearish_Below",0)
redisClient0.set("HIGH",input("Enter Local-Global High : "))
redisClient0.set("LOW",input("Enter Local-Global Low : "))
redisClient0.set("Last_Swing",input("Enter The Last Swing ( -1 For Swing Low, +1 For Swing High ): "))

generate_levels()

while True:
    ws = websocket.WebSocketApp(socket, on_message=generate_signal)
    ws.run_forever()