"""Supplied in-class demo with a second moving average and small display fixes."""
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

END = date.today()
START = END - timedelta(days=365)

st.set_page_config(layout='wide', page_title='Stock Price Analysis', page_icon='$')
st.title('Stock Analysis')
st.sidebar.title('Input')
ticker = st.sidebar.text_input('Enter stock ticker symbol', 'AAPL').strip().upper()
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input('Start Date', value=START)
end_date = col2.date_input('End Date', value=END)
mv_avg = st.sidebar.slider('Short Moving Average', 5, 200, 20, 1)
long_mv_avg = st.sidebar.slider('Long Moving Average', 5, 200, 50, 1)
run_analysis = st.sidebar.button(label='Run Analysis', type='primary')


def get_stock_data(ticker, start_date, end_date):
    try:
        data = yf.download(ticker, start_date, end_date, auto_adjust=True)
        if data is None or data.empty:
            return None, f'No data for {ticker}'
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data, f'Successfully downloaded data {ticker}'
    except Exception as e:
        return None, f'Download failed due to {e}'


if run_analysis:
    if not ticker or start_date >= end_date:
        st.error('Enter a ticker and put the start date before the end date.')
        st.stop()
    with st.spinner(f'Fetching {ticker} data...'):
        df, msg = get_stock_data(ticker, start_date, end_date)
    if df is not None:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)
        st.stop()
    df['MA'] = df['Close'].rolling(window=mv_avg).mean()
    df['MA_long'] = df['Close'].rolling(window=long_mv_avg).mean()
    df['pct_chg'] = df.Close.pct_change()
    tab1, tab2, tab3 = st.tabs(['Chart', 'Statistics', 'Raw Data'])

    with tab1:
        st.subheader(f'{ticker} Price Analysis')
        col1, col2, col3 = st.columns(3)
        col1.metric('Last Price', f'{df.Close.iloc[-1]:.2f}')
        col2.metric('Cum. Change', f'{df.Close.iloc[-1]/df.Close.iloc[0]-1:.2%}')
        col3.metric('Trading Days', f'{df.Close.count()}')
        fig = px.line(df, y=['Close', 'MA', 'MA_long'])
        fig.update_layout(hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

    with tab2:
        st.subheader(f'{ticker} Summary Statistics')
        col1, col2 = st.columns(2)
        with col1:
            st.write('**Daily Change Stats**')
            st.dataframe(df['pct_chg'].describe())
        with col2:
            st.write('**Price Stats**')
            price_stats = pd.DataFrame({
                'Metric': ['High', 'Low', 'Mean', 'Volatility'],
                'Values': [f'{df.Close.max():.2f}', f'{df.Close.min():.2f}',
                           f'{df.Close.mean():.2f}', f'{df.Close.std():.2f}']
            })
            st.dataframe(price_stats)

    with tab3:
        st.subheader(f'{ticker} Raw Data')
        st.dataframe(df)
        st.download_button('Download Raw Data', df.to_csv(),
                           file_name=f'{ticker}_Raw_Data.csv', mime='text/csv')
