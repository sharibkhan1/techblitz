from customer import analyze_portfolio
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import List

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome to the Portfolio Analysis API! Use /analyze_portfolio to analyze stock tickers."}

@app.get("/analyze_portfolio", response_class=HTMLResponse)
def analyze_portfolio_endpoint(tickers: str = Query(..., description="Comma-separated stock tickers (e.g., AAPL,GOOGL,MSFT)")):
    """API endpoint to analyze a portfolio based on user-selected tickers."""
    tickers_list = tickers.split(",")  # Convert input string into a list
    result = analyze_portfolio(tickers_list)

    # Generate HTML response
    html_content = f"""
    <html>
    <body>
        <h1>Portfolio Analysis</h1>
        <pre>{result['analysis']}</pre>
        <h2>Cumulative Returns</h2>
        <img src="data:image/png;base64,{result['cumulative_returns_plot']}" alt="Cumulative Returns">
        <h2>Daily Returns</h2>
        <img src="data:image/png;base64,{result['daily_returns_plot']}" alt="Daily Returns">
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)