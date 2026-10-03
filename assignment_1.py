"""Run with: streamlit run assignment_1.py"""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from stock import Stock


@st.cache_data(ttl=3600, show_spinner=False)
def load_stock(ticker, start_date, end_date, ma_window, long_ma_window):
    return Stock(ticker, start=start_date, end=end_date,
                 ma_window=ma_window, long_ma_window=long_ma_window)


st.set_page_config(page_title='Stock Analysis', page_icon='$', layout='wide')
st.title('Stock Analysis')
st.sidebar.header('Stock settings')
ticker = st.sidebar.text_input('Ticker symbol', 'AAPL').strip().upper()
start_date = st.sidebar.date_input(
    'Start date', value=(pd.Timestamp(date.today()) - pd.DateOffset(months=6)).date())
end_date = st.sidebar.date_input('End date', value=date.today() + timedelta(days=1))
st.sidebar.caption('Start is inclusive; end is exclusive. Prices are adjusted.')
ma_window = st.sidebar.slider('Short moving average', 5, 200, 20)
long_ma_window = st.sidebar.slider('Long moving average', 5, 200, 50)
fetch_button = st.sidebar.button('Fetch stock data', type='primary')
st.sidebar.button('Clear cached downloads', on_click=load_stock.clear)
st.sidebar.caption('After changing settings, click Fetch or Compare to update results.')

tab1, tab2 = st.tabs(['Single Stock Analysis', 'Portfolio Comparison'])

with tab1:
    st.header('Single Stock Analysis')
    if fetch_button:
        st.session_state.pop('single_stock', None)
        if not ticker or ',' in ticker or len(ticker.split()) != 1:
            st.error('Enter one ticker symbol.')
        elif start_date >= end_date:
            st.error('Start date must be before end date.')
        else:
            with st.spinner(f'Fetching {ticker}...'):
                st.session_state.single_stock = load_stock(
                    ticker, start_date, end_date, ma_window, long_ma_window)

    stock = st.session_state.get('single_stock')
    if stock is None:
        st.info('Choose your settings and click Fetch stock data.')
    elif stock.data is None:
        st.error(stock.message)
    else:
        st.success(stock.message)
        st.caption(f'Displayed request: {stock.start} to {stock.end} (end exclusive). '
                   f'Moving averages: {stock.ma_window} and {stock.long_ma_window} days.')
        col1, col2, col3 = st.columns(3)
        col1.metric('Last adjusted close', f"${stock.data['Close'].iloc[-1]:.2f}")
        col2.metric('Cumulative log return', f"{stock.data['return'].sum():.2%}")
        col3.metric('Trading days with returns', len(stock.data))
        st.caption('Log returns are rounded to four decimals by Stock. Their sum '
                   'is a cumulative log return, not a simple percentage price change.')
        price_fig = px.line(stock.data, y=['Close', 'MA', 'MA_long'],
                            title=f'{stock.symbol} price and moving averages',
                            labels={'value': 'Adjusted price (USD)', 'index': 'Date'})
        price_fig.update_layout(hovermode='x unified', legend_title_text='Series')
        st.plotly_chart(price_fig, width='stretch')
        if stock.data[['MA', 'MA_long']].isna().any().any():
            st.caption('Moving averages start after enough retained trading days. '
                       'A window longer than the available data has no visible line.')
        st.plotly_chart(stock.plot_performance(), width='stretch')
        st.plotly_chart(stock.plot_return_dist(), width='stretch')
        st.subheader('Daily log return statistics')
        st.dataframe(stock.data['return'].describe().to_frame('Daily log return'))

with tab2:
    st.header('Portfolio Comparison')
    portfolio_input = st.text_input('Comma-separated ticker symbols', 'AAPL, MSFT')
    compare_button = st.button('Compare stocks', type='primary')
    if compare_button:
        st.session_state.pop('portfolio', None)
        tickers = list(dict.fromkeys(
            symbol.strip().upper() for symbol in portfolio_input.split(',')
            if symbol.strip()))
        if not tickers:
            st.error('Enter at least one ticker symbol.')
        elif start_date >= end_date:
            st.error('Start date must be before end date.')
        else:
            stocks = []
            with st.spinner('Fetching portfolio data...'):
                for symbol in tickers:
                    stocks.append(load_stock(symbol, start_date, end_date,
                                             ma_window, long_ma_window))
            st.session_state.portfolio = (stocks, start_date, end_date)

    portfolio = st.session_state.get('portfolio')
    if portfolio is None:
        st.info('Enter tickers and click Compare stocks. Dates come from the sidebar.')
    else:
        stocks, displayed_start, displayed_end = portfolio
        valid_stocks = []
        for item in stocks:
            if item.data is None:
                st.error(item.message)
            else:
                valid_stocks.append(item)
        if valid_stocks:
            # Compare matching trading dates and use the same starting date.
            comparison = pd.concat(
                [item.zero_based_performance() for item in valid_stocks],
                axis=1, join='inner').sort_index().dropna()
            if len(comparison) < 2:
                st.warning('Not enough overlapping trading dates. Widen the date range.')
            else:
                comparison = comparison - comparison.iloc[0]
                st.caption(f'Requested: {displayed_start} to {displayed_end} '
                           f'(end exclusive). Shared trading dates: '
                           f'{comparison.index[0]:%Y-%m-%d} to '
                           f'{comparison.index[-1]:%Y-%m-%d}.')
                portfolio_fig = px.line(comparison,
                    title='Portfolio cumulative performance',
                    labels={'index': 'Date', 'value': 'Cumulative log return',
                            'variable': 'Ticker'})
                portfolio_fig.update_layout(yaxis_tickformat='.1%',
                                             hovermode='x unified')
                portfolio_fig.add_hline(y=0, line_dash='dash', opacity=0.5)
                st.plotly_chart(portfolio_fig, width='stretch')
                st.caption('Every line starts at exactly 0.0 on the first shared '
                           'trading date. Performance uses the class’s rounded log returns.')
                with st.expander('Check starting values and daily returns'):
                    st.write('Starting values')
                    st.dataframe(comparison.head(1))
                    daily_returns = pd.concat(
                        [item.data['return'].rename(item.symbol) for item in valid_stocks],
                        axis=1).reindex(comparison.index)
                    st.write('Daily log returns (decimal units; 0.01 means 1%)')
                    st.dataframe(daily_returns)
                    st.download_button('Download daily returns',
                        daily_returns.to_csv(), 'portfolio_daily_returns.csv', 'text/csv')
                    if len(valid_stocks) == 2:
                        gap = comparison.iloc[:, 0] - comparison.iloc[:, 1]
                        nonzero_gap = gap[gap.abs() > 1e-12]
                        crossings = nonzero_gap[
                            nonzero_gap * nonzero_gap.shift() < 0].index
                        st.write('Dates where the lead changed after the starting tie')
                        if len(crossings):
                            st.write(', '.join(day.strftime('%Y-%m-%d') for day in crossings))
                            st.caption('Each date is the first close after the lead changed; '
                                       'the plotted lines cross between observations.')
                        else:
                            st.write('No lead change found. Try another pair for the reflection.')
        else:
            st.warning('No tickers loaded successfully. Check the symbols or try again later.')
