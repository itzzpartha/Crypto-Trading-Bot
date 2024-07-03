import redis
import time
import math
from datetime import datetime
from fyers_api import accessToken,fyersModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def authorize():
    session=accessToken.SessionModel(client_id=credentials["client_id"],secret_key=credentials["secret_key"],redirect_uri=credentials["redirect_uri"],response_type="code", grant_type="authorization_code")
    response = session.generate_authcode()
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    driver=webdriver.Chrome(chrome_options=chrome_options)
    driver.get(response)
    if WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="row mt-3 mx-auto"]'))):
        driver.find_element_by_xpath("//input[@id='fy_client_id']").send_keys(credentials["user_id"])
        driver.find_element_by_xpath("//button[@id='clientIdSubmit']").click()
        if WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="row mx-auto mt-1"]'))):
            driver.find_element_by_xpath("//input[@id='fy_client_pwd']").send_keys(credentials["password"])
            driver.find_element_by_xpath("//button[@id='loginSubmit']").click()
            if WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//div[@id="pin-container"]'))):
                driver.find_element_by_xpath("//input[@class='mr-2 text-center form-control form-control-solid rounded focus:border-blue-400 focus:shadow-outline pin-field']").send_keys(credentials["pin"])
                driver.find_element_by_xpath("//button[@id='verifyPinSubmit']").click()
                time.sleep(5)
                current_url=driver.current_url
                driver.close()
                auth_code=current_url[(current_url.index("&auth_code=")+11):current_url.index("&state=")]
                session.set_token(auth_code)
                response = session.generate_token()
                redisClient0.set("token",response["access_token"])

def check_open_positions(time):
    fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
    length=redisClient2.llen("shortlisted_stocks")
    for i in range(length):
        token=(redisClient2.rpop("shortlisted_stocks")).decode('ascii')
        value=int(redisClient2.hget("shortlist_"+token,"value"))
        price=float(redisClient2.hget("shortlist_"+token,"price"))
        target=float(redisClient2.hget("shortlist_"+token,"target"))
        quantity=int(redisClient2.hget("shortlist_"+token,"qty"))
        sl=float(redisClient2.hget("shortlist_"+token,"sl"))
        if value==1:
            high=float(redisClient1.hget(token+"_"+str(time),"high"))
            if high>price:
                redisClient2.delete("pending_order_list",token)
                redisClient2.lpush("open_positions",token)
                data=place_target(token,quantity,-1,target)
                temp=fyers.place_order(data)
                if temp["s"]=="ok":
                    id=temp["id"]
                    redisClient2.hset("target_id",token,id)
                data=place_pending_order(token,quantity,-1,sl)
                temp=fyers.place_order(data)
                if temp["s"]=="ok":
                    id=temp["id"]
                    redisClient2.hset("sl_id",token,id)
            else:
                redisClient2.lpush("shortlisted_stocks",token)
        elif value==-1:
            low=float(redisClient1.hget(token+"_"+str(time),"low"))
            if low<price:
                redisClient2.delete("pending_order_list",token)
                redisClient2.lpush("open_positions",token)
                data=place_target(token,quantity,1,target)
                temp=fyers.place_order(data)
                if temp["s"]=="ok":
                    id=temp["id"]
                    redisClient2.hset("target_id",token,id)
                data=place_pending_order(token,quantity,1,sl)
                temp=fyers.place_order(data)
                if temp["s"]=="ok":
                    id=temp["id"]
                    redisClient2.hset("sl_id",token,id)
            else:
                redisClient2.lpush("shortlisted_stocks",token)

def exit_target_sl(time):
    fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
    length=redisClient2.llen("open_positions")
    for i in range(length):
        token=(redisClient2.rpop("open_positions")).decode('ascii')
        value=int(redisClient2.hget("shortlist_"+token,"value"))
        target=float(redisClient2.hget("shortlist_"+token,"target"))
        sl=float(redisClient2.hget("shortlist_"+token,"sl"))
        target_id=int(redisClient2.hget("target_id",token))
        sl_id=int(redisClient2.hget("sl_id",token))
        if value==1:
            high=float(redisClient1.hget(token+"_"+str(time),"high"))
            low=float(redisClient1.hget(token+"_"+str(time),"low"))
            if high>target:
                data={"id":sl_id}
                fyers.cancel_order(data)
                redisClient2.delete("target_id",token)
                redisClient2.delete("sl_id",token)
            elif low<sl:
                data={"id":target_id}
                fyers.cancel_order(data)
                redisClient2.delete("target_id",token)
                redisClient2.delete("sl_id",token)
            else:
                redisClient2.lpush("open_positions",token)           
        elif value==-1:
            high=float(redisClient1.hget(token+"_"+str(time),"high"))
            low=float(redisClient1.hget(token+"_"+str(time),"low"))
            if low<target:
                data={"id":sl_id}
                fyers.cancel_order(data)
                redisClient2.delete("target_id",token)
                redisClient2.delete("sl_id",token)
            elif high>sl:
                data={"id":target_id}
                fyers.cancel_order(data)
                redisClient2.delete("target_id",token)
                redisClient2.delete("sl_id",token)
            else:
                redisClient2.lpush("open_positions",token)

def forceful_exit():
    fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
    length=redisClient1.llen("open_positions")
    for i in range(length):
        token=(redisClient1.rpop("open_positions")).decode('ascii')
        data={"id":token}
        fyers.exit_positions(data)
        redisClient2.delete("target_id",token)
        redisClient2.delete("sl_id",token)
        
def generate_signal(mb_time,ib_time,sector,shortlist):
    fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
    sc_mb_close,sc_ib_open,sc_ib_close,sc_range_high,sc_range_low=get_mb_ib_sectoral(mb_time,ib_time,sector)
    if (sc_mb_close>sc_range_high) or (sc_mb_close<sc_range_low):
        for token in shortlist:
            if int(redisClient0.hget("switch",token))==0:
                range_high=float(redisClient0.hget("range_high",token))
                range_low=float(redisClient0.hget("range_low",token))
                mb_open,mb_high,mb_low,mb_close,ib_open,ib_high,ib_low,ib_close=get_mb_ib_stock(mb_time,ib_time,token)
                HL = round(mb_high+mb_low,2)
                hl = round(ib_high+ib_low,2)
                OC = round(mb_open+mb_close,2)
                oc = round(ib_open+ib_close,2)
                hl_m = round(mb_high-mb_low,2)
                oc_m = round(abs(mb_open-mb_close),2)
                oc_i = round(abs(ib_open-ib_close),2)
                if (oc_m>3*oc_i)and(3*oc_m>2*hl_m)and(mb_high>ib_high)and(mb_low<ib_low)and(hl_m>0.005*mb_open)and(hl_m<0.012*mb_open):
                    if (mb_close>mb_open)and(mb_high<1.01*range_high)and(HL<hl)and(OC<oc)and(ib_open>(mb_high-hl_m/3))and(ib_close>(mb_high-hl_m/3)):
                        if (mb_close>range_high)and(ib_open>range_high)and(ib_close>range_high)and(sc_mb_close>sc_range_high)and(sc_ib_open>sc_range_high)and(sc_ib_close>sc_range_high):
                            print(token)
                            x=mb_high*100+round(mb_open*0.1)
                            x=(x-x%5+5)/100
                            target=round(x+hl_m,2)
                            sl=mb_low
                            redisClient0.hset("switch",str(token),1)
                            redisClient2.lpush("shortlisted_stocks",token)
                            quantity=position_size(mb_high,sl)
                            redisClient2.hset("shortlist_"+str(token), mapping={
                                "value": 1,
                                "price": mb_high,
                                "target": target,
                                "sl":sl,
                                "threshold":ib_low,
                                "qty":quantity
                            })
                            redisClient0.hset("validate",token,0)
                            data=place_pending_order(token,quantity,1,mb_high)
                            temp=fyers.place_order(data)
                            print(temp["s"])
                            print(temp["message"])
                            if temp["s"]=="ok":
                                id=temp["id"]
                                redisClient2.hset("pending_order_list",token,id)
                    elif (mb_close<mb_open)and(mb_low>0.99*range_low)and(HL>hl)and(OC>oc)and(ib_open<(mb_low+hl_m/3))and(ib_close<(mb_low+hl_m/3)):
                        if (mb_close<range_low)and(ib_open<range_low)and(ib_close<range_low)and(sc_mb_close<sc_range_low)and(sc_ib_open<sc_range_low)and(sc_ib_close<sc_range_low):
                            print(token)
                            x=mb_low*100-round(mb_open*0.1)
                            x=(x-x%5)/100
                            target=round(x-hl_m,2)
                            sl=mb_high
                            redisClient0.hset("switch",str(token),1)
                            redisClient2.lpush("shortlisted_stocks",token)
                            quantity=position_size(mb_low,sl)
                            redisClient2.hset("shortlist_"+str(token), mapping={
                                "value": -1,
                                "price": mb_low,
                                "target": target,
                                "sl":sl,
                                "threshold":ib_high,
                                "qty":quantity 
                            })
                            redisClient0.hset("validate",token,0)
                            data=place_pending_order(token,quantity,-1,mb_low)
                            temp=fyers.place_order(data)
                            print(temp["s"])
                            print(temp["message"])
                            if temp["s"]=="ok":
                                id=temp["id"]
                                redisClient2.hset("pending_order_list",token,id)

def get_mb_ib_sectoral(mb_time,ib_time,sector):
    tk_mb=sector+"_"+str(mb_time)
    tk_ib=sector+"_"+str(ib_time)
    mb_close=float(redisClient1.hget(tk_mb,"close"))
    ib_open=float(redisClient1.hget(tk_ib,"open"))
    ib_close=float(redisClient1.hget(tk_ib,"close"))
    range_high=float(redisClient0.hget("range_high", sector))
    range_low=float(redisClient0.hget("range_low", sector))
    return mb_close,ib_open,ib_close,range_high,range_low

def get_mb_ib_stock(mb_time,ib_time,token):
    tk_mb=token+"_"+str(mb_time)
    tk_ib=token+"_"+str(ib_time)
    mb_open=float(redisClient1.hget(tk_mb,"open"))
    mb_high=float(redisClient1.hget(tk_mb,"high"))
    mb_low=float(redisClient1.hget(tk_mb,"low"))
    mb_close=float(redisClient1.hget(tk_mb,"close"))
    ib_open=float(redisClient1.hget(tk_ib,"open"))
    ib_high=float(redisClient1.hget(tk_ib,"high"))
    ib_low=float(redisClient1.hget(tk_ib,"low"))
    ib_close=float(redisClient1.hget(tk_ib,"close"))
    return mb_open,mb_high,mb_low,mb_close,ib_open,ib_high,ib_low,ib_close

def place_pending_order(token,quantity,value,price):
    p=round(price*100+value*5)/100
    data = {
                "symbol":token,
                "qty":quantity,
                "type":3,
                "side":value,
                "productType":"INTRADAY",
                "limitPrice":0,
                "stopPrice":p,
                "validity":"DAY",
                "disclosedQty":0,
                "offlineOrder":"False",
                "stopLoss":0,
                "takeProfit":0
            }
    return data

def place_target(token,quantity,value,target):
    p=round(target*100+value*5)/100
    data = {
                "symbol":token,
                "qty":quantity,
                "type":1,
                "side":value,
                "productType":"INTRADAY",
                "limitPrice":p,
                "stopPrice":0,
                "validity":"DAY",
                "disclosedQty":0,
                "offlineOrder":"False",
                "stopLoss":0,
                "takeProfit":0
            }
    return data

def position_size(price,sl):
    return(math.floor(capital*0.02/abs(price-sl)))

def remove_data(time):
    for token in [*stock_list, *index_list]:
        redisClient1.delete(token+"_"+str(time))

def screen(mb_time,ib_time):
    generate_signal(mb_time,ib_time,"NSE:NIFTYAUTO-INDEX",nifty_auto)
    generate_signal(mb_time,ib_time,"NSE:NIFTYBANK-INDEX",nifty_bank)
    generate_signal(mb_time,ib_time,"NSE:NIFTYENERGY-INDEX",nifty_energy)
    generate_signal(mb_time,ib_time,"NSE:NIFTYFINSERVICE-INDEX",nifty_finance)
    generate_signal(mb_time,ib_time,"NSE:NIFTYFMCG-INDEX",nifty_fmcg)
    generate_signal(mb_time,ib_time,"NSE:NIFTYIT-INDEX",nifty_it)
    generate_signal(mb_time,ib_time,"NSE:NIFTYMEDIA-INDEX",nifty_media)
    generate_signal(mb_time,ib_time,"NSE:NIFTYMETAL-INDEX",nifty_metal)
    generate_signal(mb_time,ib_time,"NSE:NIFTYPHARMA-INDEX",nifty_pharma)
    generate_signal(mb_time,ib_time,"NSE:NIFTYREALTY-INDEX",nifty_realty)

def validate(time):
    fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
    length=redisClient2.llen("shortlisted_stocks")
    for i in range(length):
        token=(redisClient2.rpop("shortlisted_stocks")).decode('ascii')
        value=int(redisClient2.hget("shortlist_"+token,"value"))
        threshold=float(redisClient2.hget("shortlist_"+token,"threshold"))
        vald=int(redisClient0.hget("validate",token))
        pending_id=int(redisClient2.hget("pending_order_list",token))
        data={"id":pending_id}
        if vald>1:
            redisClient2.delete("shortlist_"+token)
            fyers.cancel_order(data)
            redisClient2.delete("pending_order_list",token)
        else:
            if value==1:
                low=float(redisClient1.hget(token+"_"+str(time),"low"))
                if low < threshold:
                    redisClient2.delete("shortlist_"+token)
                    fyers.cancel_order(data)
                    redisClient2.delete("pending_order_list",token)
                else:
                    redisClient2.lpush("shortlisted_stocks",token)
                    redisClient0.hset("validate",token,vald+1)
            elif value==-1:
                high=float(redisClient1.hget(token+"_"+str(time),"high"))
                if high > threshold:
                    redisClient2.delete("shortlist_"+token)
                    fyers.cancel_order(data)
                    redisClient2.delete("pending_order_list",token)
                else:
                    redisClient2.lpush("shortlisted_stocks",token)
                    redisClient0.hset("validate",token,vald+1)

credentials = {
    "client_id":"",
    "secret_key":"",
    "redirect_uri":"",
    "user_id":"",
    "password":"",
    "two_fa":"",
    "pin":""
    }

nifty_auto = ["NSE:AMARAJABAT-EQ","NSE:ASHOKLEY-EQ","NSE:BAJAJ-AUTO-EQ","NSE:BALKRISIND-EQ","NSE:BHARATFORG-EQ","NSE:EICHERMOT-EQ","NSE:EXIDEIND-EQ","NSE:HEROMOTOCO-EQ","NSE:M&M-EQ","NSE:TATAMOTORS-EQ","NSE:TVSMOTOR-EQ"]
nifty_bank = ["NSE:AUBANK-EQ","NSE:AXISBANK-EQ","NSE:BANDHANBNK-EQ","NSE:HDFCBANK-EQ","NSE:ICICIBANK-EQ","NSE:INDUSINDBK-EQ","NSE:KOTAKBANK-EQ","NSE:RBLBANK-EQ","NSE:SBIN-EQ"]
nifty_energy = ["NSE:BPCL-EQ","NSE:GAIL-EQ","NSE:IOC-EQ","NSE:NTPC-EQ","NSE:ONGC-EQ","NSE:POWERGRID-EQ","NSE:RELIANCE-EQ","NSE:TATAPOWER-EQ"]
nifty_finance = ["NSE:CHOLAFIN-EQ","NSE:HDFC-EQ","NSE:HDFCAMC-EQ","NSE:HDFCLIFE-EQ","NSE:ICICIGI-EQ","NSE:ICICIPRULI-EQ","NSE:M&MFIN-EQ","NSE:MUTHOOTFIN-EQ","NSE:PEL-EQ","NSE:PFC-EQ","NSE:RECLTD-EQ","NSE:SBILIFE-EQ","NSE:SRTRANSFIN-EQ"]
nifty_fmcg = ["NSE:BRITANNIA-EQ","NSE:COLPAL-EQ","NSE:DABUR-EQ","NSE:GODREJCP-EQ","NSE:HINDUNILVR-EQ","NSE:ITC-EQ","NSE:MARICO-EQ","NSE:MCDOWELL-N-EQ","NSE:TATACONSUM-EQ","NSE:UBL-EQ"]
nifty_it = ["NSE:HCLTECH-EQ","NSE:INFY-EQ","NSE:MINDTREE-EQ","NSE:MPHASIS-EQ","NSE:TCS-EQ","NSE:TECHM-EQ","NSE:WIPRO-EQ"]
nifty_media = ["NSE:PVR-EQ","NSE:SUNTV-EQ","NSE:ZEEL-EQ"]
nifty_metal = ["NSE:ADANIENT-EQ","NSE:COALINDIA-EQ","NSE:HINDALCO-EQ","NSE:JINDALSTEL-EQ","NSE:JSWSTEEL-EQ","NSE:NMDC-EQ","NSE:SAIL-EQ","NSE:TATASTEEL-EQ","NSE:VEDL-EQ"]
nifty_pharma = ["NSE:ALKEM-EQ","NSE:APLLTD-EQ","NSE:AUROPHARMA-EQ","NSE:BIOCON-EQ","NSE:CADILAHC-EQ","NSE:CIPLA-EQ","NSE:DIVISLAB-EQ","NSE:DRREDDY-EQ","NSE:GLENMARK-EQ","NSE:GRANULES-EQ","NSE:IPCALAB-EQ","NSE:LAURUSLABS-EQ","NSE:LUPIN-EQ","NSE:PFIZER-EQ","NSE:STAR-EQ","NSE:SUNPHARMA-EQ","NSE:TORNTPHARM-EQ"]
nifty_realty = ["NSE:DLF-EQ","NSE:GODREJPROP-EQ","NSE:OBEROIRLTY-EQ"]

stock_list=[*nifty_auto, *nifty_bank, *nifty_energy, *nifty_finance, *nifty_fmcg, *nifty_it, *nifty_media, *nifty_metal, *nifty_pharma, *nifty_realty]
index_list = ["NSE:NIFTYAUTO-INDEX","NSE:NIFTYBANK-INDEX","NSE:NIFTYENERGY-INDEX","NSE:NIFTYFINSERVICE-INDEX","NSE:NIFTYFMCG-INDEX","NSE:NIFTYIT-INDEX","NSE:NIFTYMEDIA-INDEX","NSE:NIFTYMETAL-INDEX","NSE:NIFTYPHARMA-INDEX","NSE:NIFTYREALTY-INDEX"]
candle_duration=900
capital=10000

redisConnPool0 = redis.ConnectionPool(host='localhost', port=6379, db=0)
redisConnPool1 = redis.ConnectionPool(host='localhost', port=6379, db=1)
redisConnPool2 = redis.ConnectionPool(host='localhost', port=6379, db=2)
redisClient0 = redis.Redis(connection_pool=redisConnPool0)
redisClient1 = redis.Redis(connection_pool=redisConnPool1)
redisClient2 = redis.Redis(connection_pool=redisConnPool2)

authorize()
global access_token
access_token=(redisClient0.get("token")).decode('ascii')

for token in stock_list:
    redisClient0.hset("switch",token,0)

while True: 
    if (datetime.now().hour*60+datetime.now().minute)>570:
        time_now=round(time.time())
        range_from=time_now-candle_duration-time_now%candle_duration
        range_to=time_now
        fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
        for token in [*stock_list, *index_list]:
            data={"symbol":token,"resolution":"15","date_format":"0","range_from":range_from,"range_to":range_to,"cont_flag":"1"}
            candle_data=fyers.history(data)
            time.sleep(0.1)
            high=candle_data['candles'][0][2]
            low=candle_data['candles'][0][3]
            redisClient0.hset("range_high",token,high)
            redisClient0.hset("range_low",token,low)
        break

while True:
    time_now=round(time.time())
    if time_now%candle_duration==5:
        range_from=time_now-candle_duration-5
        range_to=time_now
        fyers = fyersModel.FyersModel(client_id=credentials["client_id"],token=access_token,log_path="C:\BingeScoop\Log")
        for token in [*stock_list, *index_list]:
            data={"symbol":token,"resolution":"15","date_format":"0","range_from":range_from,"range_to":range_to,"cont_flag":"1"}
            candle_data=fyers.history(data)
            time.sleep(0.1)
            open=candle_data['candles'][0][1]
            high=candle_data['candles'][0][2]
            low=candle_data['candles'][0][3]
            close=candle_data['candles'][0][4]
            redisClient1.hset(token+"_"+str(range_from),mapping={
                "open":open,
                "high":high,
                "low":low,
                "close":close
            })
        if datetime.now().hour>9:
            ib_time=range_from
            mb_time=ib_time-candle_duration
            exit_target_sl(ib_time)
            check_open_positions(ib_time)
            validate(ib_time)
            screen(mb_time,ib_time)
            remove_data(mb_time-candle_duration)
        if (datetime.now().hour*60+datetime.now().minute)>915:
            forceful_exit()
        else:
            continue
        break

