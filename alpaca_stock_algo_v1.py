# Importing relevant modules
import requests, re, datetime, math, datetime, schedule, time
import pandas as pd
import openpyxl as pxl
import numpy as np
import alpaca_trade_api as tradeapi
from alpaca_trade_api import StreamConn
import pandas_market_calendars as mcal
from bs4 import BeautifulSoup as soup
from yahooquery import Ticker

class TradingAlgo():
    
    def __init__(self, key_id, secret_key):
        self.version = 1.1
        self.key_id = key_id
        self.secret_key = secret_key

    def buy(self):
        print("Starting up purchasing algorithm")
        # Only trade on trading days
        nyse = mcal.get_calendar('NYSE')
        today = datetime.date.today().strftime("%Y-%m-%d")
        date_end = (datetime.date.today() + datetime.timedelta(days=250)).strftime("%Y-%m-%d")
        date_range = nyse.valid_days(start_date=today, end_date=date_end)

        if (today in date_range) == False:
            print(f"Markets are closed on {today}")
        else:
            key_id = self.key_id
            secret_key = self.secret_key
            alpaca = tradeapi.REST(key_id = key_id, secret_key = secret_key, base_url='https://api.alpaca.markets')

            ################################################################################################################

            # FIND BIGGEST STOCK MOVERS WITH PRICE >$5, VOLUME > 500K, PCT CHANGE < 15%, AND NOT TRADED OTC
            
            gains_df = pd.DataFrame()

            for i in range(0, 200, 100):
                gains_url = f"https://finance.yahoo.com/gainers/?count=100&offset={i}"
                userClient = requests.get(gains_url)
                html = userClient.text
                userClient.close()
                soup_page = soup(html, "html.parser")
                top_gains_table = soup_page.find("table",{"class":"W(100%)"})
                top_gains_df = pd.read_html(str(top_gains_table))[0]
                gains_df = pd.concat([gains_df, top_gains_df]).reset_index(drop=True)

            volume = []
            for vol in gains_df["Volume"]:
                if str(vol)[-1:] == "M":
                    volume.append(float(str(vol)[:3])*1_000_000)
                else:
                    volume.append(float(vol))
            
            gains_df["Volume"] = volume
            gains_df["pct_change"] = gains_df["% Change"].str.slice(1,-1).str.replace(",","").astype("float64")
            gains_df["Symbol Length"] = gains_df.Symbol.str.len()

            possible_stocks = gains_df[(gains_df["Price (Intraday)"] >= 5) & (gains_df["Volume"] >= 800_000) & (gains_df["pct_change"] < 15) & (gains_df["Symbol Length"] < 5)].reset_index(drop=True)
            viable_stocks = []
            for stock in possible_stocks["Symbol"]:
                try:
                    if alpaca.get_asset(stock).tradable:
                        viable_stocks.append((alpaca.get_asset(stock)).symbol)
                except:
                    pass
            trade_stocks = possible_stocks[[possible_stocks["Symbol"][i] in viable_stocks for i in range(len(possible_stocks))]].reset_index(drop=True)

            ################################################################################################################

            if len(trade_stocks) > 2:
                # ROBINHOOD STOCKS
                buying_power = float(alpaca.get_account().buying_power)
                cash_per_stock = buying_power/len(trade_stocks)

                # BUY
                for row in range(len(trade_stocks)):
                    stock_count = math.floor(cash_per_stock/trade_stocks.loc[row,"Price (Intraday)"])
                    stock_name = trade_stocks.loc[row,"Symbol"]
                    try:
                        alpaca.submit_order(stock_name, stock_count, "buy", "market", "day")
                        print(f"Success! Purchasing {stock_count} shares of {stock_name}")
                    except:
                        pass
                # Buy the same stocks with whatever buying power is left
                new_buying_power = float(alpaca.get_account().buying_power)
                new_cash_per_stock = new_buying_power/len(trade_stocks)

                for row in range(len(trade_stocks)):
                    stock_count = math.floor(new_cash_per_stock/trade_stocks.loc[row,"Price (Intraday)"])
                    stock_name = trade_stocks.loc[row,"Symbol"]
                    try:
                        alpaca.submit_order(stock_name, stock_count, "buy", "market", "day")
                        print(f"Success! Purchasing {stock_count} shares of {stock_name}")
                    except:
                        pass
                
                time.sleep(5)

                # Circumvent collared market buys
                open_orders = alpaca.list_orders(status = "open")
                if len(open_orders) > 0:
                    count = 1
                    while count < 3:
                        try:
                            open_buy_orders = alpaca.list_orders(status = "open")
                            print(f"Collared market order. Attempting to purchase again. Attempt: {count}/2")
                            print("Cancelling and repurchasing collared orders")
                            alpaca.cancel_all_orders()
                            # Try to purchase the shares again
                            for order in open_buy_orders:
                                alpaca.submit_order(order.symbol, order.qty, "buy", "market", "day")
                                print(f"Success! Repurchasing {order.qty} shares of {order.symbol}")
                            count += 1
                            time.sleep(3)
                        except:
                            count += 1
                
                alpaca.cancel_all_orders()

                # Buy SPY with whatever cash is left
                try:
                    cash_for_spy = float(alpaca.get_account().buying_power)
                    spy_price = float(alpaca.get_last_trade("SPY").price)
                    spy_quantity = math.floor(cash_for_spy/spy_price)
                    alpaca.submit_order("SPY", spy_quantity, "buy", "market", "day")
                    print(f"Success! Purchasing {spy_quantity} shares of SPY")
                except:
                    pass
                
                # Place trailing stop orders
                time.sleep(10)
                try:
                    closed_positions = alpaca.list_orders(status = "closed")
                    for position in closed_positions:
                        if position.symbol == "SPY":
                            alpaca.submit_order(symbol = position.symbol, qty = position.qty, side = "sell", type = "trailing_stop", time_in_force = "gtc", trail_percent = "0.8")
                            print(f"Success! Placed a trailing stop order to sell {position.symbol} shares of {position.qty}")
                        else:
                            alpaca.submit_order(symbol = position.symbol, qty = position.qty, side = "sell", type = "trailing_stop", time_in_force = "gtc", trail_percent = "4.5")
                            print(f"Success! Placed a trailing stop order to sell {position.symbol} shares of {position.qty}")
                except:
                    pass

            else: # Run if the portfolio isn't diversified enough
                print("Portfolio underdiversified. Waiting 5 minutes before trying again")
                time.sleep(270)

                gains_df = pd.DataFrame()

                for i in range(0, 200, 100):
                    gains_url = f"https://finance.yahoo.com/gainers/?count=100&offset={i}"
                    userClient = requests.get(gains_url)
                    html = userClient.text
                    userClient.close()
                    soup_page = soup(html, "html.parser")
                    top_gains_table = soup_page.find("table",{"class":"W(100%)"})
                    top_gains_df = pd.read_html(str(top_gains_table))[0]
                    gains_df = pd.concat([gains_df, top_gains_df]).reset_index(drop=True)

                volume = []
                for vol in gains_df["Volume"]:
                    if str(vol)[-1:] == "M":
                        volume.append(float(str(vol)[:3])*1_000_000)
                    else:
                        volume.append(float(vol))
                
                gains_df["Volume"] = volume
                gains_df["pct_change"] = gains_df["% Change"].str.slice(1,-1).str.replace(",","").astype("float64")
                gains_df["Symbol Length"] = gains_df.Symbol.str.len()

                possible_stocks = gains_df[(gains_df["Price (Intraday)"] >= 5) & (gains_df["Volume"] >= 800_000) & (gains_df["pct_change"] < 15) & (gains_df["Symbol Length"] < 5)].reset_index(drop=True)
                viable_stocks = []
                for stock in possible_stocks["Symbol"]:
                    try:
                        if alpaca.get_asset(stock).tradable:
                            viable_stocks.append((alpaca.get_asset(stock)).symbol)
                    except:
                        pass
                trade_stocks = possible_stocks[[possible_stocks["Symbol"][i] in viable_stocks for i in range(len(possible_stocks))]].reset_index(drop=True)

                ################################################################################################################

                if len(trade_stocks) > 2:
                    # ROBINHOOD STOCKS
                    buying_power = float(alpaca.get_account().buying_power)
                    cash_per_stock = buying_power/len(trade_stocks)

                    # BUY
                    for row in range(len(trade_stocks)):
                        stock_count = math.floor(cash_per_stock/trade_stocks.loc[row,"Price (Intraday)"])
                        stock_name = trade_stocks.loc[row,"Symbol"]
                        try:
                            alpaca.submit_order(stock_name, stock_count, "buy", "market", "day")
                            print(f"Success! Purchasing {stock_count} shares of {stock_name}")
                        except:
                            pass

                    # Buy the same stocks with whatever buying power is left
                    new_buying_power = float(alpaca.get_account().buying_power)
                    new_cash_per_stock = new_buying_power/len(trade_stocks)

                    for row in range(len(trade_stocks)):
                        stock_count = math.floor(new_cash_per_stock/trade_stocks.loc[row,"Price (Intraday)"])
                        stock_name = trade_stocks.loc[row,"Symbol"]
                        try:
                            alpaca.submit_order(stock_name, stock_count, "buy", "market", "day")
                            print(f"Success! Purchasing {stock_count} shares of {stock_name}")
                        except:
                            pass
                    
                    time.sleep(5)

                    # Circumvent collared market buys
                    open_orders = alpaca.list_orders(status = "open")
                    if len(open_orders) > 0:
                        count = 1
                        while count < 3:
                            try:
                                open_buy_orders = alpaca.list_orders(status = "open")
                                print(f"Collared market order. Attempting to purchase again. Attempt: {count}/2")
                                print("Cancelling and repurchasing collared orders")
                                alpaca.cancel_all_orders()
                                # Try to purchase the shares again
                                for order in open_buy_orders:
                                    alpaca.submit_order(order.symbol, order.qty, "buy", "market", "day")
                                    print(f"Success! Repurchasing {order.qty} shares of {order.symbol}")
                                count += 1
                                time.sleep(3)
                            except:
                                count += 1

                    alpaca.cancel_all_orders()

                    try:
                        cash_for_spy = float(alpaca.get_account().buying_power)
                        spy_price = float(alpaca.get_last_trade("SPY").price)
                        spy_quantity = math.floor(cash_for_spy/spy_price)
                        alpaca.submit_order("SPY", spy_quantity, "buy", "market", "day")
                        print(f"Success! Purchasing {spy_quantity} shares of SPY")
                    except:
                        pass
                    
                    # Place trailing stop orders
                    time.sleep(10)
                    try:
                        closed_positions = alpaca.list_orders(status = "closed")
                        for position in closed_positions:
                            if position.symbol == "SPY":
                                alpaca.submit_order(symbol = position.symbol, qty = position.qty, side = "sell", type = "trailing_stop", time_in_force = "gtc", trail_percent = "0.8")
                                print(f"Success! Placed a trailing stop order to sell {position.symbol} shares of {position.qty}")
                            else:
                                alpaca.submit_order(symbol = position.symbol, qty = position.qty, side = "sell", type = "trailing_stop", time_in_force = "gtc", trail_percent = "4.5")
                                print(f"Success! Placed a trailing stop order to sell {position.symbol} shares of {position.qty}")
                    except:
                        pass

                else: # If the portfolio still isn't diversified enough, cancel all orders and stop trading for the day. Robinhood can't distinguish mid to large cap stocks
                    print("Too risky to invest in anything today. Will try again in another trading day")
        print("Purchasing algorithm complete")

    def sell(self):
        print("Starting up selling algorithm")
        nyse = mcal.get_calendar('NYSE')
        today = datetime.date.today().strftime("%Y-%m-%d")
        date_end = (datetime.date.today() + datetime.timedelta(days=250)).strftime("%Y-%m-%d")
        date_range = nyse.valid_days(start_date=today, end_date=date_end)
        if (today in date_range) == False:
            print(f"Markets are closed on {today}")
        else:
            # SELL
            key_id = self.key_id
            secret_key = self.secret_key
            alpaca = tradeapi.REST(key_id = key_id, secret_key = secret_key, base_url='https://api.alpaca.markets')
            alpaca.cancel_all_orders()
            while alpaca.list_positions() != []:
                portfolio = alpaca.list_positions()
                for position in portfolio:
                    alpaca.submit_order(position.symbol, position.qty, "sell", "market", "gtc")
                    print(f"Sucess! Selling {position.qty} shares of {position.symbol}")
                time.sleep(10)
                alpaca.cancel_all_orders() # cancel all stock orders to avoid double selling
            print("All stock orders cancelled and positions sold")

# ALL TIMES ARE IN EST
schedule.clear('daily-tasks')
schedule.every().day.at("09:35").do(TradingAlgo.buy).tag('daily-tasks')
schedule.every().day.at("15:55").do(TradingAlgo.sell).tag('daily-tasks')

while True:
    schedule.run_pending()
    time.sleep(5)
