
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8")
import tpqoa
import math

class IterativeBase():
    ''' Base class for the iterative backtesting trading strategies.

    Attributes
    ==========
    config: str
        file location of config
    symbol: str
        ticker symbol with which to work with
    start: str/datetime
        start date for data retrieval
    end: str/datetime
        end date for data retrieval
    amount: integer
        amount in account
    use_spread: boolean
        whether to use spread to account for trading costs
        

    Methods
    =======
    get_data:
        retrieves and prepares the data

    plot_data:
        plots columns inputted as a timeseries
    
    get_values:
        returns the date, the price and the spread for the given bar.

    print_current_balance:
        prints out the current (cash) balance.

    full_report:
        gives full report of buying and selling of most recent strategy tested

    buy_instrument:
        places and executes a buy order (market order).
    
    sell_instrument:
        places and executes a sell order (market order).

    print_current_position_value
        prints out the current position value.
    
    print_current_nav:
        prints out the current net asset value (nav).

    close_pos:
        closes out a long or short position (go neutral).
    '''
        
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
        self.lines = 0

        attempt = 0
        success = False       
        while True: 
            try:
                self.get_data()
            except Exception as e:
                print (e, end = "|")
            else:
                success = True
                break
            finally:
                attempt += 1
                print ("Attempt: {}".format(attempt), end="\n")
                if success == False:
                    if attempt >= 5:
                        print ("5 attempts reached. Please check your connection and try again")
                        break   
    
    def get_data(self):
        ''' Retrieves and prepares the data
        '''

        ask_data = self.api.get_history(instrument=self.symbol, start=self.start, end=self.end, granularity=self.granularity, price="A")
        bid_data = self.api.get_history(instrument=self.symbol, start=self.start, end=self.end, granularity=self.granularity, price="B")

        ask_close = ask_data[["c"]]
        bid_close = bid_data[["c"]]

        df = pd.DataFrame()
        df["price"] = (ask_close + bid_close) / 2

        df["spread"] = ask_close.sub(bid_close).dropna()

        df["returns"] = np.log(df.price / df.price.shift(1))

        self.data = df

    def plot_data(self, cols, axes_labels, title=None, start = None, end=None):
        ''' Plots columns inputted as a timeseries

        Parameters
        ==========
        cols: ndarray
            array of columns to plot
        
        axes_labels: ndarray
            array of axes labels

        title: str
            title for plot
        
        start: str/datetime
            first point to plot
        
        end: str/datetime
            last point to plot
        '''
        if start == None:
            start = self.data.index[0]
        
        if end == None:
            end = self.data.index[-1]

        if title == None:
            title = self.symbol

        data = self.data[start:end].copy()
        cols = data[cols]
        
        GREY30 = "#4d4d4d"
        GREY40 = "#474747"
        GREY60 = "#999999"
        GREY91 = "#e8e8e8"
        GREY98 = "#fafafa"

        palette = plt.get_cmap('Paired')

        fig, ax = plt.subplots()

        for i, col in enumerate(cols):
            ax.plot(data.index, data[col], marker='', color=palette((i+1)%palette.N), linewidth=1, alpha=0.9)

        ax.set_title(title, loc='center', fontsize=12, weight='bold', color=GREY40)
        ax.set_xlabel(axes_labels[0], color=GREY40)
        ax.set_ylabel(axes_labels[1], color=GREY40)

        ax.spines["left"].set_color(GREY91)
        ax.spines["right"].set_color("none")
        ax.spines["top"].set_color("none")
        ax.spines["bottom"].set_color(GREY91)

        fig.patch.set_facecolor(GREY98)
        ax.set_facecolor(GREY98)


        time_delta = data.index[-1] - data.index[0]
            
        if time_delta > pd.Timedelta(days=365):
            date_range = pd.date_range(start=start, end=end, freq='6M')

        elif time_delta > pd.Timedelta(days=28):
            date_range = pd.date_range(start=start, end=end, freq='M')

        elif time_delta > pd.Timedelta(hours=24):
            date_range = pd.date_range(start=start, end=end, freq='D')

        else:
            date_range = pd.date_range(start=start, end=end, freq='H')

        # Plot vertical lines at each time unit change
        for v in date_range:
            ax.axvline(x=v, color=GREY60, linewidth=0.6, alpha=0.5)
        ax.grid(False)
        y_min, y_max = ax.get_ylim()
        y_min = 1 if y_min > 1 else y_min * 0.75
        y_max = math.ceil(y_max) * 0.75 if math.ceil(y_max) * 0.75 > y_max else math.ceil(y_max)
        ax.hlines(y=np.arange(y_min, y_max, step=0.1), xmin=data.index[0], xmax=data.index[-1], color=GREY60, lw=0.6)

        # ax.set_ylim(y_min, y_max*0.8)

        # Last value in y (where to point to)
        y_starts = [data[col][-1] for col in cols]

        # Last value in x (where to start the line)
        x_start = data.index[-1]
        x_end = x_start + pd.Timedelta(days=int(len(data)/8))
        names = cols.columns

        for i in range(0, len(names)):
            text = "    " + names[i]
            y = y_starts[i]
            ax.plot([x_start, x_end], [y, y], color=palette((i+1)%palette.N), alpha=0.5, ls="dashed", lw=0.6)
            
            ax.text(x_end, y, text, va="center")

        # Show the graph
        plt.tight_layout()
        plt.show()
    
    def get_values(self, bar):
        ''' Returns the date, the price and the spread for the given bar.

        Parameters
        ==========
        bar: int
            bar to get values for
        '''
        date = str(self.data.index[bar].date())
        price = round(self.data.price.iloc[bar], 5)
        spread = round(self.data.spread.iloc[bar], 5)
        return date, price, spread
    
    def print_current_balance(self, bar):
        ''' Prints out the current (cash) balance.
        
        Parameters
        ==========
        bar: int
            bar to get value for
        '''
        date, price, spread = self.get_values(bar)
        print("{} | Current Balance: {}".format(date, round(self.current_balance, 2)))
    
    def full_report(self):
        ''' Updates SMA parameters and returns the negative absolute performance (for minimazation algorithm).
        '''
        for sentence in self.report:
            print (sentence)
        
    def buy_instrument(self, bar, units = None, amount = None):
        ''' Places and executes a buy order (market order).

        Parameters
        ==========
        bar: int
            bar to get values for

        units: int
            number of units to buy

        amount: int
            ammount to  buy
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

        Parameters
        ==========
        bar: int
            bar to get values for

        units: int
            number of units to sell

        amount: int
            ammount to sell
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

        Parameters
        ==========
        bar: int
            bar to get values for
        '''
        date, price, spread = self.get_values(bar)
        cpv = self.units * price
        print("{} |  Current Position Value = {}".format(date, round(cpv, 2)))
    
    def print_current_nav(self, bar):
        ''' Prints out the current net asset value (nav).

        Parameters
        ==========
        bar: int
            bar to get values for
        '''
        date, price, spread = self.get_values(bar)
        nav = self.current_balance + self.units * price
        print("{} |  Net Asset Value = {}".format(date, round(nav, 2)))
        
    def close_pos(self, bar):
        ''' Closes out a long or short position (go neutral).

        Parameters
        ==========
        bar: int
            bar to get values for
        '''
        date, price, spread = self.get_values(bar)

        lines = "-" * self.lines
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