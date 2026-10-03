import numpy as np
import pandas as pd
import plotly.express as px
import yfinance as yf


class Stock:

    def __init__(self,symbol, start, end, ma_window=10 ):
        self.symbol = symbol
        self.start = start
        self.end = end
        self.ma_window = ma_window
        self.data, self.message = self.get_data()

    def get_data(self):
        try:
            data = yf.download(self.symbol,
                               start=self.start,
                               end=self.end,
                               progress=False,
                               multi_level_index=False)
            if data.empty:
                return None, f"No data for {self.symbol}"
            data = self._calc_returns(data)
            data = self._calc_ma(data, self.ma_window)
            return data, f"Successfully downloaded for {self.symbol}"
        except Exception as e:
            return None, f"Failed due to {e}"

    def _calc_returns(self, df):
        df['change'] = df['Close'] - df['Close'].shift(1)
        df['return'] =np.log(df['Close']).diff().round(4)
        return df.dropna()


    def _calc_ma(self, df,window):
        df['MA'] = df['Close'].rolling(window=window).mean()
        return df

    def plot_return_dist(self):
        """return plotly histogram showing dist of daily returns"""
        mean_return = self.data['return'].mean()
        fig = px.histogram(self.data['return'],
                           nbins= 35,
                           title=f"Distribution of daily returns for {self.symbol}",
                           labels={'value':'Return', 'count': 'Frequency'},
                           opacity=0.85, # sets transparency between 0 and 1
                           color_discrete_sequence=['#1f77b4'] #overrides default color
                            )
        fig.update_traces(marker_line_color='rgb(255,255,255)',
                          marker_line_width=0.5)
        # mean vertical line plot
        fig.add_vline(x=mean_return,
                      line_dash='dash',
                      line_color='red',
                      annotation_text=f'Mean: {mean_return:.2f}',
                      annotation_position='top right')
        return fig

    def plot_performance(self):
        """plot cum performance of a stock"""

        performance = self.data['return'].cumsum()
        fig = px.line(x=performance.index,
                      y=performance.values,
                      title=f"Performance of {self.symbol}",
                      labels={'x':'Date', 'y': 'Cum Return'})
        fig.update_traces(line=dict(color="#2ca02c", width=2))
        fig.add_hline(y=0,line_dash='dash',line_color='black',opacity=0.7)
        fig.update_layout(yaxis_tickformat='.1%', hovermode='x unified')
        return fig


# --- For development testing only ---
def main():
    test = Stock("AAPL", "2025-09-24","2026-09-23")
    print(test.data)
    # print(test.message)
    hist = test.plot_return_dist()
    hist.show()
    perf = test.plot_performance()
    perf.show()


if __name__ == '__main__':
    main()