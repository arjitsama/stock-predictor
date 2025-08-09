# import the necessary libraries
import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import date
from prophet import Prophet
from plotly import graph_objs as go

# data from 2015 to today
START = "2015-01-01"
TODAY = date.today().strftime("%Y-%m-%d")

st.title('Stock Predictor')

# pick a stock ticker
tickers = [
    ' ', 'TSLA', 'GOOGL', 'UBER', 'SHOP', 'MSFT', 'PYPL',
    'AMZN', 'AAPL', 'META', 'LYFT', 'NVDA', 'NFLX', 'AMD', 'INTC', 'BABA',
    'ADBE', 'TWTR', 'ORCL'
]

st.markdown("#### Select a stock to predict its price")
selected_stock = st.selectbox("Select a popular ticker", tickers)
custom_ticker = st.text_input("Or enter a custom ticker", "")
st.markdown("[Click to view all stock symbols](https://finance.yahoo.com/lookup/)")

if custom_ticker:
    selected_stock = custom_ticker.upper()
    if selected_stock not in tickers:
        st.warning("Custom ticker not found in the list. Please select a valid ticker.")
        selected_stock = ' '

# Check if a stock is selected
if selected_stock == ' ':
    st.warning("Please select a stock to proceed.")
else:
    @st.cache_data
    def loadData(ticker):
        df = yf.Ticker(ticker)
        df = df.history(period="max")
        return df

    df = loadData(selected_stock)

    st.subheader('Raw Data')

    def cleanData(df):
        df = df.copy()
        df.drop(columns=["Dividends", "Stock Splits"], inplace=True, errors="ignore")
        df.index = pd.to_datetime(df.index)
        df.index = df.index.strftime('%Y-%m-%d')
        st.write(df.tail())
        return df

    df = cleanData(df)

    # plot raw prices
    st.subheader("Plot of Stock Prices")

    def plot_raw_data():
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Open'], name="stock_open"))
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="stock_close"))
        fig.layout.update(title_text='Time Series Data', xaxis_rangeslider_visible=True)
        st.plotly_chart(fig)

    plot_raw_data()

    st.subheader("Stock Price Forecast")

    # predicting with Prophet
    def predict_stock(df, years):
        prophet_df = df[['Close']].copy()
        prophet_df['ds'] = pd.to_datetime(df.index)
        prophet_df.rename(columns={"Close": "y"}, inplace=True)

        # initialize and train model
        model = Prophet(changepoint_prior_scale=0.5)
        model.fit(prophet_df)

        # Future df
        future_periods = years * 365
        future = model.make_future_dataframe(periods=future_periods)
        forecast = model.predict(future)

        # Return prediction df
        forecast_df = forecast[['ds', 'yhat']].rename(columns={"ds": "Date", "yhat": "Predicted Close"})
        return forecast_df

    # slider: 1-5 years
    years_to_predict = st.slider("How many years into the future do you want to predict?", 1, 5, 1)
    
    # button to press to predict
    if st.button("Click to Predict"):
        forecast_df = predict_stock(df, years_to_predict)

        st.subheader(f"{selected_stock} Stock Forecast for {years_to_predict} Year(s)")

        # prepare actual data
        actual_df = df[['Close']].copy()
        actual_df['Date'] = pd.to_datetime(actual_df.index)
        actual_df.rename(columns={"Close": "Actual Close"}, inplace=True)

        # split predictions into future only
        cutoff_date = actual_df['Date'].max()
        future_predictions = forecast_df[forecast_df['Date'] > cutoff_date].copy()

        # Make future prediction line start exactly at last actual close price
        if not future_predictions.empty:
            future_predictions.iloc[0, future_predictions.columns.get_loc('Predicted Close')] = actual_df.loc[actual_df['Date'] == cutoff_date, 'Actual Close'].values[0]

        # Predicted prices plot
        fig2 = go.Figure()

        # Actual prices
        fig2.add_trace(go.Scatter(
            x=actual_df['Date'],
            y=actual_df['Actual Close'],
            mode='lines',
            name='Actual Close',
            line=dict(color='lightblue')
        ))

        # Predicted prices - future
        fig2.add_trace(go.Scatter(
            x=future_predictions['Date'],
            y=future_predictions['Predicted Close'],
            mode='lines',
            name='Predicted (Future)',
            line=dict(color='pink')
        ))

        # plot info
        fig2.update_layout(
            title="Actual vs Predicted Stock Price",
            xaxis_title="Date",
            yaxis_title="Stock Price",
            xaxis_rangeslider_visible=True
        )

        st.plotly_chart(fig2)
