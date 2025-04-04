from flask import Flask, render_template, request, send_file
from waitress import serve
import pandas as pd
import io
from historical_fetch import scrap_data, kiteLogin  # Your existing logic

app = Flask(__name__)

# Load symbols once
nse_instruments = pd.read_csv("https://api.kite.trade/instruments/NSE")
nfo_instruments = pd.read_csv("https://api.kite.trade/instruments/NFO")
nse_stocks = list(nse_instruments["tradingsymbol"].unique())
nfo_stocks = list(nfo_instruments["tradingsymbol"].unique())
all_symbols = sorted(set(nse_stocks + nfo_stocks))

@app.route("/")
def index():
    return render_template("index.html", stocks=all_symbols)

@app.route("/download", methods=["POST"])
def download():
    symbol = request.form["symbol"]
    timeframe = request.form["timeframe"]

    token = kiteLogin()
    df = scrap_data(token, symbol, timeframe)

    if df.empty:
        return "No data found", 400

    # Convert DataFrame to CSV in bytes
    csv_string = df.to_csv(index=False)
    buffer = io.BytesIO(csv_string.encode("utf-8"))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{symbol}_{timeframe}.csv",
        mimetype="text/csv"
    )

import os

if __name__ == "__main__":
    mode = os.getenv("FLASK_ENV", "development")
    if mode == "production":
        app.run(host="0.0.0.0", port=8052, debug=True)
    else:
        app.run(host="0.0.0.0", port=8052, debug=True)