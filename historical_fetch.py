import time 
import requests
import datetime as dt
import pandas as pd
import requests
import pyotp
import json
from dotenv import load_dotenv
import os

load_dotenv()

user_id = os.getenv("Z_USER_ID")
pswd = os.getenv("Z_PASSWORD")
totp = os.getenv("Z_TOTP_KEY")


#vlookup for instrument token
nse_instruments = pd.read_csv("https://api.kite.trade/instruments/NSE")
data = nse_instruments[['instrument_token','tradingsymbol']]
inst = data.set_index('tradingsymbol')

#Get all NFO stocks
nfo_instruments = pd.read_csv("https://api.kite.trade/instruments/NFO")
nfo_stocks = list(nfo_instruments[nfo_instruments["instrument_type"] == "FUT"]["name"].unique())

# lookup for timeframe
TimeFrame = [
    "minute",
    "3minute",
    "5minute",
    "10minute",
    "15minute",
    "30minute",
    "60minute",
    "day",
]

def kiteLogin():  # automated login
  # print("Logging in...")
  user_id = "VT5229"
  pswd = "Zerodha@4321"
  totp_key = "XUNNWCF6EF7BJR5GFW6XCYT4Z2D33ROI"
  twofa = pyotp.TOTP(totp_key).now()
  sesh2 = requests.Session()
  url = "https://kite.zerodha.com/api/login"
  twofaUrl = "https://kite.zerodha.com/api/twofa"
  reqId = json.loads(sesh2.post(url, {"user_id": user_id, "password": pswd}).text)["data"]["request_id"]
  # print(reqId)
  time.sleep(3)
  login = sesh2.post(twofaUrl, {"user_id": user_id, "request_id": reqId, "twofa_value": twofa})
  # print(login)
  time.sleep(2)
  reqToken = sesh2.get("https://kite.zerodha.com/oms/user/margins")
  # print(reqToken.request.headers['Cookie'])
  a = reqToken.request.headers['Cookie']
  
  
  for i in a.split():
    if "enctoken" in i:
        enctoken = i.split(';')[0].replace('=', ' ', 1)
        token = enctoken.split(" ")[-1]
        print(token)
        break
    
  return token

# Function to get last 60 days of data
def get_data(token, period, start_date, end_date, symbol):

    scrip_ID = inst.loc[symbol]["instrument_token"]
    url = f"https://kite.zerodha.com/oms/instruments/historical/{scrip_ID}/{period}?user_id={user_id}&oi=1&from={start_date}&to={end_date}"

    payload = {}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "authorization": f"enctoken {token}",
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # this condition was added because Zerodha started sending html data instead of Json data when requests were made at this frequency
    if (
        response.headers["content-type"] == "text/html; charset=UTF-8"
        or len(response.json()["data"]["candles"]) == 0
    ):
        return "fail"
    else:
        data = response.json()["data"]["candles"]
        return data
    
# Function to scrap whole data
def scrap_data(token, scrip_name, period):

    err_count = 0

    scrip_name = str(scrip_name)
    df = pd.DataFrame(columns=["DateTime", "Open", "High", "Low", "Close", "Volume"])

    final_start = "2015-01-01"
    start = dt.datetime.strptime(final_start, "%Y-%m-%d")
    end = start + dt.timedelta(60)

    diff = divmod((dt.datetime.today() - end).total_seconds(), 86400)[0]

    while diff >= 0:

        start_date = dt.datetime.strftime(start, "%Y-%m-%d")
        end_date = dt.datetime.strftime(end, "%Y-%m-%d")

        a = get_data(token, period, start_date, end_date, scrip_name)

        # condition if we do not receive the data from the API
        if a == "fail":

            time.sleep(1)
            err_count += 1
            # st.write(err_count)

            # if the data does not come after 5 iterations, then switch to the next date
            if err_count > 5:
                diff = divmod((dt.datetime.today() - end).total_seconds(), 86400)[0]

                if diff < 0:
                    start = end + dt.timedelta(1)
                    end = start + dt.timedelta(abs(diff))
                else:
                    start = end + dt.timedelta(1)
                    end = start + dt.timedelta(60)

            else:
                continue

        # if API gave the correct API response
        else:
            err_count = 0

            data = pd.DataFrame(
                a, columns=["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
            )
            data.drop(columns=["OI"], inplace=True)

            # Drop all-NA columns and rows from data
            data_cleaned = data.dropna(axis=1, how='all').dropna(axis=0, how='all')

            # Same for df (optional, only if you're building df from scratch)
            df_cleaned = df.dropna(axis=1, how='all').dropna(axis=0, how='all')

            # Now only concatenate if data_cleaned is non-empty with valid columns
            if not data_cleaned.empty and len(data_cleaned.columns) > 0:
                df = pd.concat([df_cleaned, data_cleaned], ignore_index=True)

            diff = divmod((dt.datetime.today() - end).total_seconds(), 86400)[0]

            if diff < 0:
                start = end + dt.timedelta(1)
                end = start + dt.timedelta(abs(diff))
            else:
                start = end + dt.timedelta(1)
                end = start + dt.timedelta(60)

# Split DateTime column into separate Date and Time columns
    df[["Date", "Time"]] = df["DateTime"].str.split("T", expand=True)
    df["Time"] = df["Time"].str.split("+").str[0]  # remove timezone offset if any

    # Drop the original DateTime and optional OI
    df.drop(columns=["DateTime"], inplace=True)

    # Reorder columns (optional)
    df = df[["Date", "Time", "Open", "High", "Low", "Close", "Volume"]]

    # Optional: don't set Date as index if you're exporting CSV
    # (because indexing makes it harder to work in Excel)
    
    return df
