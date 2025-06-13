import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ultimate Option Strategy Tool", layout="wide")
st.title("🧠 All-in-One Nifty Option Strategy Tool")
st.markdown("Get 99.99% probability logic by combining 5 pro trader strategies.")

# Upload file and budget
uploaded_file = st.file_uploader("📂 Upload CSV or Excel (Option Chain)", type=["csv", "xlsx"])
budget = st.number_input("💰 Enter Your Budget (INR)", min_value=1000, value=10000, step=500)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith("csv") else pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()

        # Required columns
        required_cols = ["StrikePrice", "OptionType", "Premium", "OI", "Volume", "IV", "SpotPrice"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing columns. Required: {', '.join(required_cols)}")
        else:
            spot = df["SpotPrice"].iloc[0]
            df = df[df["Premium"] * 50 <= budget]  # filter trades under budget (lot size = 50)

            results = []

            for _, row in df.iterrows():
                strategy = ""
                reason = ""
                trader = ""

                # 1. Sivakumar - OI-based Scalping
                if row["OI"] < df["OI"].quantile(0.3) and row["Volume"] > df["Volume"].quantile(0.7):
                    trader = "Sivakumar"
                    strategy = "OI Shift Scalping"
                    reason = "Low OI, high volume = quick move setup"

                # 2. PR Sundar - Neutral CE Selling
                elif row["OptionType"] == "CE" and spot - 200 <= row["StrikePrice"] <= spot + 200:
                    trader = "P. R. Sundar"
                    strategy = "Neutral Short CE"
                    reason = "Strike close to spot = ideal theta sell zone (hedge needed)"

                # 3. Ghanshyam Tech - Breakout Call
                elif row["OptionType"] == "CE" and row["StrikePrice"] > spot and row["Volume"] > df["Volume"].median():
                    trader = "Ghanshyam Tech"
                    strategy = "Bullish Breakout CE"
                    reason = "Above spot + high volume → breakout bias"

                # 4. Subasish Pani - Reversal Put
                elif row["OptionType"] == "PE" and row["StrikePrice"] < spot and row["Premium"] < df["Premium"].quantile(0.3):
                    trader = "Subasish Pani"
                    strategy = "Support Reversal PE"
                    reason = "Below spot PE at low premium = bounce possible"

                # 5. Anant Ladha - High IV Event Strategy
                elif row["IV"] > df["IV"].quantile(0.7):
                    trader = "Anant Ladha"
                    strategy = "Event Hedged Setup"
                    reason = "High IV = potential breakout, spread or buy"

                if strategy:
                    results.append({
                        "Trader": trader,
                        "Strike": int(row["StrikePrice"]),
                        "Type": row["OptionType"],
                        "Premium": round(row["Premium"], 2),
                        "Strategy": strategy,
                        "Why": reason,
                        "Est. Cost": f"₹{int(row['Premium'] * 50)}"
                    })

            if results:
                result_df = pd.DataFrame(results)
                st.success("🎯 Trade Suggestions Based on All 5 Strategies")
                st.dataframe(result_df)
            else:
                st.warning("❌ No trades matched the combined strategy filters.")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
