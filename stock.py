import numpy as np
import pandas as pd
import plotly.express as px
import yfinance as yf


class Stock:
    def __init__(self, symbol, start=None, end=None, ma_window=10,
                 long_ma_window=50):
        self.symbol = symbol.strip().upper()
        self.start = start
        self.end = end
        self.ma_window = ma_window
        self.long_ma_window = long_ma_window
        self.baseline_date = None
        self.data, self.message = self.get_data()

    def get_data(self):
        try:
            data = yf.download(self.symbol, start=self.start, end=self.end,
                               progress=False, multi_level_index=False,
                               auto_adjust=True)
            if data is None or data.empty:
                return None, f"No data for {self.symbol}"
            data = data.sort_index().dropna(subset=['Close']).copy()
            data = data.loc[data['Close'] > 0].copy()
            if len(data) < 2:
                return None, f"{self.symbol}: choose a range with at least two trading days."
            # Keep the original first date before _calc_returns drops its row.
            self.baseline_date = data.index[0]
            data = self._calc_returns(data)
            data = self._calc_ma(data, self.ma_window)
            data['MA_long'] = data['Close'].rolling(
                window=self.long_ma_window).mean()
            return data, f"Successfully downloaded for {self.symbol}"
        except Exception as e:
            return None, f"{self.symbol}: download or calculation failed: {e}"

    def _calc_returns(self, df):
        df = df.copy()
        df['change'] = df['Close'] - df['Close'].shift(1)
        df['return'] = np.log(df['Close']).diff().round(4)
        return df.dropna(subset=['change', 'return']).copy()

    def _calc_ma(self, df, window):
        df['MA'] = df['Close'].rolling(window=window).mean()
        return df

    def zero_based_performance(self):
        """Include the first downloaded trading date at exactly zero."""
        performance = self.data['return'].cumsum()
        baseline = pd.Series([0.0], index=[self.baseline_date])
        return pd.concat([baseline, performance]).rename(self.symbol)

    def plot_return_dist(self):
        """Return a Plotly histogram of daily log returns."""
        mean_return = self.data['return'].mean()
        fig = px.histogram(self.data, x='return', nbins=35,
                           title=f"Distribution of daily returns for {self.symbol}",
                           labels={'return': 'Daily log return'}, opacity=0.85,
                           color_discrete_sequence=['#1f77b4'])
        fig.update_traces(marker_line_color='rgb(255,255,255)',
                          marker_line_width=0.5)
        fig.add_vline(x=mean_return, line_dash='dash', line_color='red',
                      annotation_text=f'Mean: {mean_return:.2%}',
                      annotation_position='top right')
        fig.update_layout(xaxis_tickformat='.1%', yaxis_title='Frequency')
        return fig

    def plot_performance(self):
        """Preserve the supplied class's cumulative log return chart."""
        performance = self.data['return'].cumsum()
        fig = px.line(x=performance.index, y=performance.values,
                      title=f"Performance of {self.symbol}",
                      labels={'x': 'Date', 'y': 'Cumulative log return'})
        fig.update_traces(line=dict(color='#2ca02c', width=2))
        fig.add_hline(y=0, line_dash='dash', line_color='black', opacity=0.7)
        fig.update_layout(yaxis_tickformat='.1%', hovermode='x unified')
        return fig


if __name__ == '__main__':
    test = Stock('AAPL', '2025-09-24', '2026-09-23')
    print(test.message)
    if test.data is not None:
        print(test.data)
        test.plot_return_dist().show()
        test.plot_performance().show()
