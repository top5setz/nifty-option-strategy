
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Offline Nifty Option Strategy Tool", layout="wide")

# --- Header ---
st.markdown("<h1 style='text-align:center;color:#004d99;'>📈 Offline Nifty Option Strategy Analyzer</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Sidebar Inputs ---
st.sidebar.header("📊 Input Configuration")
uploaded_file = st.sidebar.file_uploader("Upload Option Chain File (.csv or .xlsx)", type=["csv", "xlsx"])
budget = st.sidebar.number_input("Budget (INR)", min_value=1000, value=10000, step=500)
show_charts = st.sidebar.checkbox("Show Charts", True)

def fetch_option_chain_offline(uploaded_file, budget):
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df = df.rename(columns={
            "StrikePrice": "StrikePrice",
            "Type": "type",
            "LTP": "LTP",
            "OI": "OI",
            "ChngOI": "ChngOI",
            "Volume": "Volume",
            "IV": "IV"
        })

        df["Cost"] = df["LTP"] * 50
        df = df[df["Cost"] <= budget]
        spot_price = df.loc[df["Volume"].idxmax(), "StrikePrice"]
        return df, spot_price
    except Exception as e:
        st.error(f"❌ Failed to read option data: {e}")
        return pd.DataFrame(), 0

if uploaded_file:
    df_chain, spot_price = fetch_option_chain_offline(uploaded_file, budget)
    st.sidebar.write(f"📌 Inferred Spot Price: `{spot_price}`")

    # Strategy Logic
    st.markdown("### 🔍 Single-leg Trade Ideas Based on Top Traders")
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
        st.warning("No trade signals found based on strategy filters.")

    # Spread Strategy
    st.markdown("### 📐 Spread Strategy Ideas (Bull Call & Bear Put)")
    spread_ideas = []

    ce_df = df_chain[df_chain["type"] == "CE"].sort_values("StrikePrice")
    for i in range(len(ce_df) - 1):
        buy = ce_df.iloc[i]
        sell = ce_df.iloc[i + 1]
        if buy["StrikePrice"] < spot_price:
            spread_ideas.append({
                "Strategy": "Bull Call Spread", "Buy CE": buy["StrikePrice"], "Sell CE": sell["StrikePrice"],
                "Net Cost": round((buy["LTP"] - sell["LTP"]) * 50, 2),
                "Max Profit": round((sell["StrikePrice"] - buy["StrikePrice"]) * 50 - (buy["LTP"] - sell["LTP"]) * 50, 2)
            })

    pe_df = df_chain[df_chain["type"] == "PE"].sort_values("StrikePrice", ascending=False)
    for i in range(len(pe_df) - 1):
        buy = pe_df.iloc[i]
        sell = pe_df.iloc[i + 1]
        if buy["StrikePrice"] > spot_price:
            spread_ideas.append({
                "Strategy": "Bear Put Spread", "Buy PE": buy["StrikePrice"], "Sell PE": sell["StrikePrice"],
                "Net Cost": round((buy["LTP"] - sell["LTP"]) * 50, 2),
                "Max Profit": round((buy["StrikePrice"] - sell["StrikePrice"]) * 50 - (buy["LTP"] - sell["LTP"]) * 50, 2)
            })

    if spread_ideas:
        st.dataframe(pd.DataFrame(spread_ideas))
    else:
        st.info("No spread setups matching current filter conditions.")

    if show_charts:
        st.markdown("### 📊 OI and IV Visuals")
        for opt_type in ["CE", "PE"]:
            subset = df_chain[df_chain["type"] == opt_type]
            chart = alt.Chart(subset).mark_circle(size=60).encode(
                x="StrikePrice", y="OI",
                color=alt.Color("IV", scale=alt.Scale(scheme="viridis")),
                tooltip=["StrikePrice", "OI", "Volume", "IV", "LTP"]
            ).properties(title=f"{opt_type} - OI vs IV")
            st.altair_chart(chart, use_container_width=True)

else:
    st.warning("📥 Please upload a valid Option Chain file to begin analysis.")
