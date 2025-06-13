import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt

st.set_page_config(page_title="Nifty Option Strategy Analyzer", layout="wide", page_icon="📊")

# --- Header ---
st.markdown("""
<h1 style='text-align: center; color: #003366;'>📊 Nifty & BankNifty Option Analyzer (All-in-One)</h1>
""", unsafe_allow_html=True)
st.markdown("---")

# --- Sidebar ---
st.sidebar.header("⚙️ Controls")
symbol = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])
expiry = st.sidebar.text_input("Expiry Date (e.g., 26-Jun-2025)", "26-Jun-2025")
budget = st.sidebar.number_input("Budget (INR)", min_value=1000, value=10000, step=500)
show_charts = st.sidebar.checkbox("Show Charts", True)

@st.cache_data(ttl=60)
def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    s = requests.Session()
    s.get("https://www.nseindia.com", headers=headers)
    response = s.get(url, headers=headers)
    data = response.json()["records"]["data"]
    records = []
    spot = response.json()["records"]["underlyingValue"]
    for item in data:
        if "CE" in item:
            ce = item["CE"]
            ce["type"] = "CE"
            ce["StrikePrice"] = item["strikePrice"]
            records.append(ce)
        if "PE" in item:
            pe = item["PE"]
            pe["type"] = "PE"
            pe["StrikePrice"] = item["strikePrice"]
            records.append(pe)
    df = pd.DataFrame(records)
    df.rename(columns={
        "openInterest": "OI",
        "changeinOpenInterest": "ChngOI",
        "totalTradedVolume": "Volume",
        "impliedVolatility": "IV",
        "lastPrice": "LTP"
    }, inplace=True)
    df["Cost"] = df["LTP"] * 50
    return df, spot

df_chain, spot_price = fetch_option_chain(symbol)
st.sidebar.write(f"Spot Price: {spot_price}")
df_chain = df_chain[df_chain["Cost"] <= budget]

# --- Strategy Engine ---
st.markdown("### 🎯 Single-leg Trade Ideas")
strategies = []
for _, row in df_chain.iterrows():
    t, strat, reason = "", "", ""
    if row["OI"] < df_chain["OI"].quantile(0.3) and row["Volume"] > df_chain["Volume"].quantile(0.7):
        t, strat, reason = "Sivakumar", "Scalping", "Low OI & high volume"
    elif row["type"] == "CE" and abs(row["StrikePrice"] - spot_price) <= 200:
        t, strat, reason = "P. R. Sundar", "Neutral CE Sell", "Strike near spot"
    elif row["type"] == "CE" and row["StrikePrice"] > spot_price:
        t, strat, reason = "Ghanshyam Tech", "Breakout", "Call breakout above spot"
    elif row["type"] == "PE" and row["StrikePrice"] < spot_price:
        t, strat, reason = "Subasish Pani", "Reversal PE Buy", "Below spot PE buy"
    elif row["IV"] > df_chain["IV"].quantile(0.7):
        t, strat, reason = "Anant Ladha", "Hedged Play", "High IV event setup"
    if strat:
        strategies.append({
            "Trader": t, "Strike": row["StrikePrice"], "Type": row["type"],
            "LTP": row["LTP"], "IV": row["IV"], "Cost": row["Cost"], "Strategy": strat, "Reason": reason
        })

df_strat = pd.DataFrame(strategies)
if not df_strat.empty:
    st.dataframe(df_strat)
else:
    st.warning("No single-leg trades found.")

# --- Spread Engine ---
st.markdown("### 🧮 Spread Opportunities")

spread_ideas = []
ce_df = df_chain[df_chain["type"] == "CE"].sort_values("StrikePrice")
for i in range(len(ce_df) - 1):
    buy = ce_df.iloc[i]
    sell = ce_df.iloc[i + 1]
    if buy["StrikePrice"] < spot_price:
        spread_ideas.append({
            "Strategy": "Bull Call Spread", "Trader": "Anant Ladha",
            "Buy CE": buy["StrikePrice"], "Sell CE": sell["StrikePrice"],
            "Net Cost": round((buy["LTP"] - sell["LTP"]) * 50, 2),
            "Max Profit": round((sell["StrikePrice"] - buy["StrikePrice"]) * 50 - (buy["LTP"] - sell["LTP"]) * 50, 2)
        })

pe_df = df_chain[df_chain["type"] == "PE"].sort_values("StrikePrice", ascending=False)
for i in range(len(pe_df) - 1):
    buy = pe_df.iloc[i]
    sell = pe_df.iloc[i + 1]
    if buy["StrikePrice"] > spot_price:
        spread_ideas.append({
            "Strategy": "Bear Put Spread", "Trader": "Subasish Pani",
            "Buy PE": buy["StrikePrice"], "Sell PE": sell["StrikePrice"],
            "Net Cost": round((buy["LTP"] - sell["LTP"]) * 50, 2),
            "Max Profit": round((buy["StrikePrice"] - sell["StrikePrice"]) * 50 - (buy["LTP"] - sell["LTP"]) * 50, 2)
        })

if spread_ideas:
    st.dataframe(pd.DataFrame(spread_ideas))
else:
    st.info("No spreads match current filters.")

# --- Charts ---
if show_charts:
    st.markdown("### 📊 Option Analytics")
    for opt_type in ["CE", "PE"]:
        subset = df_chain[df_chain["type"] == opt_type]
        chart = alt.Chart(subset).mark_circle(size=60).encode(
            x="StrikePrice", y="OI",
            color=alt.Color("IV", scale=alt.Scale(scheme="viridis")),
            tooltip=["StrikePrice", "OI", "Volume", "IV", "LTP"]
        ).properties(title=f"{opt_type} Chart: OI vs IV")
        st.altair_chart(chart, use_container_width=True)
