import streamlit as st
import pandas as pd
from ai_portfolio_builder import AIPortfolioBuilder

st.set_page_config(page_title="EGX AI Portfolio", layout="wide")

st.title("🤖📈 EGX AI Portfolio Builder")
st.markdown("كوّن محفظة استثمارية في البورصة المصرية باستخدام الذكاء الاصطناعي.")

# ---------------------------------------------------------
# الكون الافتراضي لأسهم البورصة المصرية
# ---------------------------------------------------------
DEFAULT_UNIVERSE = [
    "COMI", "ETEL", "EKHO", "AMOC", "CIEB", "SWDY",
    "ORHD", "ESRS", "FWRY", "HRHO", "EFIH", "ADIB",
    "DICE", "CCAP", "ABUK"
]

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("إعدادات المحفظة")

mode = st.sidebar.radio(
    "نوع الذكاء الاصطناعي المستخدم:",
    ["بسيط (توزيع متساوي)", "ذكي (عائد/مخاطرة تاريخية)"]
)

capital = st.sidebar.number_input(
    "المبلغ المستثمر (EGP)",
    min_value=1000.0,
    value=100000.0,
    step=1000.0
)

selected_universe = st.sidebar.multiselect(
    "اختر أسهم من البورصة المصرية:",
    options=DEFAULT_UNIVERSE,
    default=DEFAULT_UNIVERSE[:10]
)

lookback_days = st.sidebar.number_input(
    "عدد الأيام التاريخية (Lookback Days)",
    min_value=60,
    max_value=365,
    value=180,
    step=30
)

max_stocks = st.sidebar.number_input(
    "أقصى عدد أسهم في المحفظة",
    min_value=3,
    max_value=20,
    value=8
)

max_weight_per_stock = st.sidebar.slider(
    "أقصى وزن لسهم واحد (%)",
    min_value=5,
    max_value=50,
    value=20
) / 100.0

build_button = st.button("🚀 كوّن المحفظة الآن بالذكاء الاصطناعي")

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------
if build_button:
    if not selected_universe:
        st.error("من فضلك اختر أسهماً أولاً.")
    else:
        with st.spinner("جاري التحميل وبناء المحفظة..."):

            try:
                # ---------------------------------------------------------
                # 1) الذكاء البسيط = توزيع متساوي بين الأسهم
                # ---------------------------------------------------------
                if mode.startswith("بسيط"):

                    builder = AIPortfolioBuilder(
                        universe=selected_universe,
                        lookback_days=lookback_days,
                        auto_suffix=True,
                        verbose=False
                    )

                    equal_weight = 1.0 / len(selected_universe)
                    rows = []

                    for sym in selected_universe:
                        price = builder.egx.get_last_price(sym)
                        if price is None:
                            continue

                        alloc = capital * equal_weight
                        shares = int(alloc // price)
                        mv = shares * price

                        rows.append({
                            "symbol": sym,
                            "weight_target": equal_weight,
                            "last_price": price,
                            "shares": shares,
                            "market_value": mv
                        })

                    df = pd.DataFrame(rows)
                    total_mv = df["market_value"].sum()

                    if total_mv > 0:
                        df["weight_real"] = df["market_value"] / total_mv
                    else:
                        df["weight_real"] = 0.0

                    cash_left = capital - total_mv

                # ---------------------------------------------------------
                # 2) الذكاء الذكي = عائد / مخاطر تاريخية
                # ---------------------------------------------------------
                else:

                    builder = AIPortfolioBuilder(
                        universe=selected_universe,
                        lookback_days=lookback_days,
                        auto_suffix=True,
                        verbose=False
                    )

                    df, cash_left = builder.build_portfolio(
                        capital=capital,
                        max_stocks=max_stocks,
                        max_weight_per_stock=max_weight_per_stock
                    )

                # ---------------------------------------------------------
                # عرض النتائج
                # ---------------------------------------------------------
                st.success("تم تكوين المحفظة بنجاح ✅")
                st.info(f"نوع الذكاء المستخدم: **{mode}**")

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📊 تفاصيل المحفظة")
                    st.dataframe(df, use_container_width=True)

                with col2:
                    st.subheader("🎯 الأوزان بعد التقريب")
                    if "weight_real" in df.columns:
                        chart_data = pd.Series(
                            df["weight_real"].values,
                            index=df["symbol"]
                        )
                        st.bar_chart(chart_data)

                st.markdown("---")
                total_mv = df["market_value"].sum()

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("قيمة الأسهم", f"{total_mv:,.2f} EGP")
                with col_b:
                    st.metric("الكاش المتبقي", f"{cash_left:,.2f} EGP")
                with col_c:
                    st.metric("إجمالي المحفظة", f"{(total_mv + cash_left):,.2f} EGP")

            except Exception as e:
                st.error(f"حدث خطأ أثناء بناء المحفظة: {e}")

else:
    st.info("اختر الإعدادات واضغط على زر (كوّن المحفظة الآن).")
