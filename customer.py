from fastapi import FastAPI, Query, HTTPException
from typing import List
import yfinance as yf
import pandas as pd
from fastapi.responses import HTMLResponse
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from openai import OpenAI  # Import the new OpenAI client
from dotenv import load_dotenv  # Import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# Function to analyze portfolio
def analyze_portfolio(tickers: List[str]):
    try:
        start_date = '2016-01-01'
        end_date = '2024-05-01'

        # Ensure tickers are formatted correctly
        tickers_list = [ticker.strip().upper() for ticker in tickers if ticker.strip()]
        if not tickers_list:
            raise HTTPException(status_code=400, detail="Invalid tickers provided.")

        # Download stock data
        try:
            print("Downloading data for tickers:", tickers_list)
            data = yf.download(tickers_list, start=start_date, end=end_date, group_by='ticker')
            print("Data downloaded successfully.")
            print("Data columns:", data.columns)  # Debugging: Print columns
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching stock data: {str(e)}")

        # Handle missing or incorrect data
        if data.empty:
            raise HTTPException(status_code=404, detail="No valid stock data found. Check the ticker symbols.")

        # Extract "Close" for each ticker (since "Adj Close" is not available with group_by='ticker')
        close_data = pd.DataFrame()
        for ticker in tickers_list:
            if ticker in data:
                print(f"Extracting 'Close' for ticker: {ticker}")
                close_data[ticker] = data[ticker]['Close']
            else:
                raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker}")

        print("Close Data:")
        print(close_data.head())  # Debugging: Print first few rows of close data

        # Drop tickers with entirely missing data
        close_data = close_data.dropna(axis=1, how='all')
        if close_data.empty:
            raise HTTPException(status_code=400, detail="None of the tickers have valid historical data.")

        # Calculate portfolio returns
        returns = close_data.pct_change().dropna()
        if returns.empty:
            raise HTTPException(status_code=500, detail="Portfolio returns could not be calculated.")

        # Assign equal weights to each stock
        weights = [1 / len(returns.columns)] * len(returns.columns)
        portfolio_returns = returns.dot(weights)

        # Ensure proper datetime index
        portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
        portfolio_returns = portfolio_returns.dropna()

        if portfolio_returns.empty:
            raise HTTPException(status_code=500, detail="Portfolio returns could not be calculated.")

        # Generate a summary of portfolio returns for OpenAI
        summary_stats = portfolio_returns.describe().to_string()
        prompt = f"Analyze the following portfolio returns statistics and provide insights:\n{summary_stats}\n\nProvide a detailed analysis of the portfolio's performance, risk, and any recommendations."

        # Call OpenAI API
        try:
            print("Calling OpenAI API...")
            response = client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 or GPT-3.5-turbo
                messages=[
                    {"role": "system", "content": "You are a financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            analysis = response.choices[0].message.content
            print("OpenAI response received.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calling OpenAI API: {str(e)}")

        # Generate graphs
        plt.figure(figsize=(10, 6))

        # Plot cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod() - 1
        plt.plot(cumulative_returns, label="Cumulative Returns")
        plt.title("Cumulative Portfolio Returns")
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")
        plt.legend()

        # Save the plot to a BytesIO object
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        cumulative_returns_plot = base64.b64encode(buf.read()).decode("utf-8")

        # Plot daily returns
        plt.figure(figsize=(10, 6))
        plt.plot(portfolio_returns, label="Daily Returns", color="orange")
        plt.title("Daily Portfolio Returns")
        plt.xlabel("Date")
        plt.ylabel("Daily Returns")
        plt.legend()

        # Save the plot to a BytesIO object
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        daily_returns_plot = base64.b64encode(buf.read()).decode("utf-8")

        return {
            "analysis": analysis,
            "cumulative_returns_plot": cumulative_returns_plot,
            "daily_returns_plot": daily_returns_plot
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))