import streamlit as st
import pandas as pd
from ai_portfolio_builder_v2 import AIPortfolioBuilderV2

# ---------------------------------------------------------
# إعداد صفحة التطبيق
# ---------------------------------------------------------
st.set_page_config(page_title="EGX AI Portfolio V2", layout="wide")

# ---------------------------------------------------------
# صفحة الدخول (Login)
# ---------------------------------------------------------
def check_login():
    USERNAME = "dr_ahmed"
    PASSWORD = "EGX2025"

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        # لو بالفعل مسجل دخول، نكمل عادي
        return True

    st.markdown(
        """
        <div style="text-align:center; margin-top:30px;">
            <h1 style="color:#0F766E; margin-bottom:5px;">Secure Access – Dr. Ahmed Salama</h1>
            <p style="color:#555;">
                يرجى إدخال بيانات الدخول للوصول إلى منصة الذكاء الاصطناعي لمحافظ البورصة المصرية.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("اسم المستخدم", value="", placeholder="مثال: dr_ahmed")
        password = st.text_input("كلمة المرور", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("تسجيل الدخول ✅")

        if submitted:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.success("تم تسجيل الدخول بنجاح ✅")
                st.rerun()
            else:
                st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                st.stop()

    st.stop()

# أول حاجة نتحقق من اللوجين
check_login()

# ---------------------------------------------------------
# لو وصلنا هنا يبقى الدخول صحيح – نعرض المنصة V2
# ---------------------------------------------------------

st.title("📊 EGX AI Portfolio Builder V2")
st.markdown(
    "هذه النسخة المتقدمة تستخدم نموذج **متعدد العوامل**: "
    "عائد/مخاطرة + أساسيات (Fundamentals) + زخم (Momentum)"
)

# الكون الافتراضي لأسهم البورصة المصرية
DEFAULT_UNIVERSE = [
    "COMI", "ETEL", "EKHO", "AMOC", "CIEB", "SWDY",
    "ORHD", "ESRS", "FWRY", "HRHO", "EFIH", "ADIB",
    "DICE", "CCAP", "ABUK"
]

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("إعدادات المحفظة (V2)")

capital = st.sidebar.number_input(
    "المبلغ المستثمر (EGP)",
    min_value=1000.0,
    value=100000.0,
    step=5000.0
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

build_button = st.sidebar.button("🚀 كوّن محفظة V2 متعددة العوامل")

# ---------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------
if build_button:
    if not selected_universe:
        st.error("من فضلك اختر أسهماً أولاً.")
    else:
        with st.spinner("جاري تحميل البيانات وبناء المحفظة المتقدمة..."):
            try:
                builder = AIPortfolioBuilderV2(
                    universe=selected_universe,
                    lookback_days=lookback_days,
                    auto_suffix=True,
                    verbose=False
                )

                # بناء المحفظة
                df, cash_left = builder.build_portfolio(
                    capital=capital,
                    max_stocks=max_stocks,
                    max_weight_per_stock=max_weight_per_stock
                )

                st.success("✅ تم تكوين المحفظة المتقدمة V2 بنجاح")

                col1, col2 = st.columns(2)

                # -------- جدول المحفظة --------
                with col1:
                    st.subheader("📊 تفاصيل المحفظة (V2)")
                    st.dataframe(df, use_container_width=True)

                # -------- رسم الأوزان --------
                with col2:
                    st.subheader("🎯 أوزان المحفظة (بعد التقريب)")
                    if "weight_real" in df.columns:
                        weights_series = pd.Series(
                            df["weight_real"].values,
                            index=df["symbol"]
                        )
                        st.bar_chart(weights_series)
                    else:
                        st.info("لا توجد أوزان محسوبة.")

                # -------- ملخص المحفظة --------
                st.markdown("---")
                total_mv = df["market_value"].sum()

                st.subheader("📘 ملخص المحفظة المتقدمة")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("قيمة الأسهم", f"{total_mv:,.2f} EGP")
                with col_b:
                    st.metric("الكاش المتبقي", f"{cash_left:,.2f} EGP")
                with col_c:
                    st.metric("إجمالي (أسهم + كاش)", f"{(total_mv + cash_left):,.2f} EGP")

                # -------- جدول العوامل (Factors) --------
                if hasattr(builder, "last_factor_df") and builder.last_factor_df is not None:
                    st.markdown("---")
                    st.subheader("🧠 تحليل العوامل لكل سهم (Risk / Fundamentals / Momentum)")

                    fact = builder.last_factor_df.copy()

                    # تحويل العائد والتذبذب إلى نسب مئوية
                    if "annual_return" in fact.columns:
                        fact["annual_return_pct"] = (fact["annual_return"] * 100).round(2)
                    if "annual_vol" in fact.columns:
                        fact["annual_vol_pct"] = (fact["annual_vol"] * 100).round(2)

                    show_cols = []
                    col_map = {}

                    if "symbol" in fact.columns:
                        show_cols.append("symbol")
                        col_map["symbol"] = "السهم"

                    if "annual_return_pct" in fact.columns:
                        show_cols.append("annual_return_pct")
                        col_map["annual_return_pct"] = "العائد السنوي (%)"

                    if "annual_vol_pct" in fact.columns:
                        show_cols.append("annual_vol_pct")
                        col_map["annual_vol_pct"] = "التذبذب السنوي (%)"

                    if "risk_score" in fact.columns:
                        show_cols.append("risk_score")
                        col_map["risk_score"] = "Risk Score"

                    if "fund_score" in fact.columns:
                        show_cols.append("fund_score")
                        col_map["fund_score"] = "Fundamentals Score"

                    if "mom_score" in fact.columns:
                        show_cols.append("mom_score")
                        col_map["mom_score"] = "Momentum Score"

                    if "total_score" in fact.columns:
                        show_cols.append("total_score")
                        col_map["total_score"] = "الدرجة النهائية (Total Score)"

                    if show_cols:
                        fact = fact[show_cols].rename(columns=col_map)
                        st.dataframe(fact, use_container_width=True)
                    else:
                        st.info("لا توجد بيانات تفصيلية للعوامل.")

            except Exception as e:
                st.error(f"حدث خطأ أثناء بناء المحفظة المتقدمة: {e}")
else:
    st.info("اضبط الإعدادات من اليسار ثم اضغط على زر (🚀 كوّن محفظة V2 متعددة العوامل).")
