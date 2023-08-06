
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8")
import tpqoa

class IterativeBase():

    def __init__(self, config, symbol, start, end, granularity, amount, use_spread = True):

        self.config = config
        self.api = tpqoa.tpqoa(config)
        self.symbol = symbol
        self.start = start
        self.end = end
        self.granularity = granularity
        self.initial_balance = amount
        self.current_balance = amount
        self.units = 0
        self.trades = 0
        self.position = 0
        self.use_spread = use_spread
        self.report = []
        self.get_data()
    
    def get_data(self):
        ask_data = self.api.get_history(instrument=self.symbol, start=self.start, end=self.end, granularity=self.granularity, price="A")
        bid_data = self.api.get_history(instrument=self.symbol, start=self.start, end=self.end, granularity=self.granularity, price="B")
        
        ask_close = ask_data[["c"]]
        bid_close = bid_data[["c"]]

        df = pd.DataFrame()
        df["price"] = (ask_close + bid_close) / 2

        df["spread"] = ask_close.sub(bid_close).dropna()

        df["returns"] = np.log(df.price / df.price.shift(1))

        self.data = df

    def plot_data(self, cols = None):  
        ''' Plots the closing price for the symbol.
        '''
        if cols is None:
            cols = "price"

        # Change the style of plot
        plt.style.use('seaborn-darkgrid')
        
        # Create a color palette
        palette = plt.get_cmap('Set1')
        
        # Plot multiple lines
        num=0
        for col in cols:
            num+=1
            plt.plot(self.data.index, self.data[col], marker='', color=palette(num), linewidth=1, alpha=0.9, label=col)

        # Add legend
        plt.legend(loc=2, ncol=2)
        
        # Add titles
        plt.title(self.symbol, loc='left', fontsize=12, fontweight=0, color='orange')

        # Show the graph
        plt.show()
        # self.data[cols].plot(figsize = (12, 8), title = self.symbol)
    
    def get_values(self, bar):
        ''' Returns the date, the price and the spread for the given bar.
        '''
        date = str(self.data.index[bar].date())
        price = round(self.data.price.iloc[bar], 5)
        spread = round(self.data.spread.iloc[bar], 5)
        return date, price, spread
    
    def print_current_balance(self, bar):
        ''' Prints out the current (cash) balance.
        '''
        date, price, spread = self.get_values(bar)
        print("{} | Current Balance: {}".format(date, round(self.current_balance, 2)))
    
    def full_report(self):
        
        for sentence in self.report:
            print (sentence)
        
    def buy_instrument(self, bar, units = None, amount = None):
        ''' Places and executes a buy order (market order).
        '''
        date, price, spread = self.get_values(bar)
        if self.use_spread:
            price += spread/2 # ask price
        if amount is not None: # use units if units are passed, otherwise calculate units
            units = int(amount / price)
        self.current_balance -= units * price # reduce cash balance by "purchase price"
        self.units += units
        self.trades += 1
        
        self.report.append("{} |  Buying {} for {}".format(date, units, round(price, 5)))
    
    def sell_instrument(self, bar, units = None, amount = None):
        ''' Places and executes a sell order (market order).
        '''
        date, price, spread = self.get_values(bar)
        if self.use_spread:
            price -= spread/2 # bid price
        if amount is not None: # use units if units are passed, otherwise calculate units
            units = int(amount / price)
        self.current_balance += units * price # increases cash balance by "purchase price"
        self.units -= units
        self.trades += 1
        
        self.report.append("{} |  Selling {} for {}".format(date, units, round(price, 5)))
        
    
    def print_current_position_value(self, bar):
        ''' Prints out the current position value.
        '''
        date, price, spread = self.get_values(bar)
        cpv = self.units * price
        print("{} |  Current Position Value = {}".format(date, round(cpv, 2)))
    
    def print_current_nav(self, bar):
        ''' Prints out the current net asset value (nav).
        '''
        date, price, spread = self.get_values(bar)
        nav = self.current_balance + self.units * price
        print("{} |  Net Asset Value = {}".format(date, round(nav, 2)))
        
    def close_pos(self, bar):
        ''' Closes out a long or short position (go neutral).
        '''
        date, price, spread = self.get_values(bar)

        lines = 75 * "-"
        self.report.append(lines)

        header = "{} | +++ CLOSING FINAL POSITION +++".format(date)
        print (header)
        self.report.append(header)

        self.current_balance += self.units * price # closing final position (works with short and long!)
        self.current_balance -= (abs(self.units) * spread/2 * self.use_spread) # substract half-spread costs

        final = "{} | closing position of {} for {}".format(date, self.units, price)
        print (final)
        self.report.append(final)

        self.units = 0 # setting position to neutral
        self.trades += 1
        perf = (self.current_balance - self.initial_balance) / self.initial_balance * 100
        self.print_current_balance(bar)
        net = "{} | net performance (%) = {}".format(date, round(perf, 2) )
        print (net)
        self.report.append(net)

        no_trades = "{} | number of trades executed = {}".format(date, self.trades)
        print (no_trades)
        self.report.append(no_trades)

        print (lines)
        self.report.append(lines)