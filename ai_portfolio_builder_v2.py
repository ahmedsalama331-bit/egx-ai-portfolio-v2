import numpy as np
import pandas as pd
from egx_yahoo import EGXYahoo


class AIPortfolioBuilderV2:
    """
    نموذج ذكاء اصطناعي متقدّم (Multi-Factor) لمحفظة EGX:
    - عامل العائد/المخاطرة (Risk-Adjusted Return)
    - عامل الأساسيات Fundamentals (من Yahoo لو متوفر)
    - عامل الزخم Momentum (1M, 3M, 6M)

    أوزان العوامل (حسب اختيارك):
    - 20% Risk-Adjusted
    - 50% Fundamentals
    - 30% Momentum
    """

    def __init__(self, universe, lookback_days=180, auto_suffix=True, verbose=True):
        self.universe = list(universe)
        self.lookback_days = lookback_days
        self.egx = EGXYahoo(self.universe, auto_suffix=auto_suffix, verbose=verbose)
        self.verbose = verbose

        # أوزان العوامل
        self.w_risk = 0.20
        self.w_fund = 0.50
        self.w_mom = 0.30

        # هنخزن آخر جدول عوامل لعرضه في الواجهة
        self.last_factor_df = None

    def _log(self, msg):
        if self.verbose:
            print(msg)

    # ------------------------------------------------------------------
    # 1) تاريخ الأسعار لكل سهم
    # ------------------------------------------------------------------
    def _get_price_history(self):
        """
        الحصول على تاريخ الأسعار لكل سهم في الكون باستخدام egx.get_price(symbol).
        نرجع dict: {symbol: Series}
        """
        print("بدء تحميل البيانات...")
        history = {}

        for sym in self.universe:
            try:
                print(f"جلب البيانات للسهم: {sym}")
                s = self.egx.get_price(sym)
            except Exception as e:
                self._log(f"⚠️ خطأ أثناء جلب الأسعار للسهم {sym}: {e}")
                continue

            if s is None or len(s) == 0:
                self._log(f"⚠️ لا توجد بيانات تاريخية للسهم: {sym}")
                continue

            # نأخذ آخر lookback_days
            if len(s) > self.lookback_days:
                s = s.iloc[-self.lookback_days:]

            s = s.dropna()
            if len(s) < 2:
                self._log(f"⚠️ عدد النقاط قليل جداً للسهم: {sym}")
                continue

            history[sym] = s

        print("تم تحميل البيانات بنجاح!")
        return history

    # ------------------------------------------------------------------
    # 2) حساب العائد السنوي والتذبذب السنوي لكل سهم
    # ------------------------------------------------------------------
    def _compute_return_risk(self, history_dict):
        print("حساب العائد والمخاطرة...")
        rows = []

        for sym, s in history_dict.items():
            daily_ret = s.pct_change().dropna()
            if daily_ret.empty:
                continue

            mean_daily = float(daily_ret.mean())
            daily_vol = float(daily_ret.std())

            annual_return = (1 + mean_daily) ** 250 - 1
            annual_vol = daily_vol * np.sqrt(250)

            if np.isnan(annual_return) or np.isnan(annual_vol) or annual_vol == 0:
                continue

            risk_score_raw = annual_return / (annual_vol + 1e-6)

            rows.append({
                "symbol": sym,
                "annual_return": annual_return,
                "annual_vol": annual_vol,
                "risk_score_raw": risk_score_raw
            })

        print("تم حساب العائد والمخاطرة!")
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame.from_records(rows)
        return df

    # ------------------------------------------------------------------
    # 3) حساب زخم السعر Momentum لكل سهم (1M, 3M, 6M)
    # ------------------------------------------------------------------
    def _compute_momentum(self, history_dict):
        print("حساب الزخم السعري...")
        rows = []

        for sym, s in history_dict.items():
            s = s.dropna()
            if len(s) < 22:
                self._log(f"⚠️ البيانات غير كافية للسهم {sym} لحساب الزخم.")
                continue

            last = float(s.iloc[-1])

            def safe_mom(back_days):
                if len(s) <= back_days:
                    return np.nan
                prev = float(s.iloc[-back_days])
                if prev == 0:
                    return np.nan
                return (last / prev) - 1.0

            mom_1m = safe_mom(21)   # تقريباً شهر
            mom_3m = safe_mom(63)   # تقريباً 3 شهور
            mom_6m = safe_mom(126)  # تقريباً 6 شهور

            vals = [mom_1m, mom_3m, mom_6m]
            vals_clean = [v for v in vals if not np.isnan(v)]
            if not vals_clean:
                self._log(f"⚠️ البيانات غير كافية لحساب الزخم للسهم {sym}.")
                continue

            # استخدام قيمة بديلة إذا كانت القيم غير موجودة
            mom_score_raw = 0.5 * (mom_1m if not np.isnan(mom_1m) else 0) + \
                            0.3 * (mom_3m if not np.isnan(mom_3m) else 0) + \
                            0.2 * (mom_6m if not np.isnan(mom_6m) else 0)

            rows.append({
                "symbol": sym,
                "mom_1m": mom_1m,
                "mom_3m": mom_3m,
                "mom_6m": mom_6m,
                "mom_score_raw": mom_score_raw
            })

        print("تم حساب الزخم السعري!")
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame.from_records(rows)
        return df

    # ------------------------------------------------------------------
    # 4) حساب Score للأساسيات Fundamentals
    # ------------------------------------------------------------------
    def _compute_fundamental_scores(self):
        print("حساب الأساسيات...")
        if not hasattr(self.egx, "get_fundamentals"):
            return {sym: 0.5 for sym in self.universe}

        raw_scores = {}
        for sym in self.universe:
            try:
                fd = self.egx.get_fundamentals(sym)
            except Exception as e:
                self._log(f"⚠️ خطأ في جلب الأساسيات للسهم {sym}: {e}")
                continue

            if not fd or not isinstance(fd, dict):
                raw_scores[sym] = 0.5  # قيمة بديلة للأساسيات
                continue

            # الحسابات الأخرى للأساسيات هنا
            score = 0.0
            weight_sum = 0.0

            pe = fd.get("pe") or fd.get("PE")
            if pe is not None and pe > 0:
                if 5 <= pe <= 20:
                    score += 1.0
                elif 0 < pe < 5 or 20 < pe <= 30:
                    score += 0.5
                weight_sum += 1.0

            pb = fd.get("pb") or fd.get("PB")
            if pb is not None and pb > 0:
                if 0.5 <= pb <= 3:
                    score += 1.0
                elif 0.2 < pb < 0.5 or 3 < pb <= 5:
                    score += 0.5
                weight_sum += 1.0

            roe = fd.get("roe") or fd.get("ROE")
            if roe is not None:
                if roe >= 0.15:
                    score += 1.0
                elif 0.08 <= roe < 0.15:
                    score += 0.5
                weight_sum += 1.0

            de = fd.get("de_ratio") or fd.get("de") or fd.get("DE")
            if de is not None and de > 0:
                if de <= 1:
                    score += 1.0
                elif 1 < de <= 2:
                    score += 0.5
                weight_sum += 1.0

            eps_g = fd.get("eps_growth") or fd.get("EPS_G")
            if eps_g is not None:
                if eps_g > 0:
                    score += 1.0
                weight_sum += 1.0

            if weight_sum == 0:
                continue

            raw_scores[sym] = score / weight_sum  # بين 0 و 1 تقريباً

        print("تم حساب الأساسيات!")
        return raw_scores

    # ------------------------------------------------------------------
    # 5) تطبيع القيم بين 0 و 1 (min-max)
    # ------------------------------------------------------------------
    @staticmethod
    def _min_max_normalize(series):
        arr = np.array(series, dtype=float)
        if len(arr) == 0:
            return np.array([])

        min_v = np.nanmin(arr)
        max_v = np.nanmax(arr)

        if np.isnan(min_v) or np.isnan(max_v) or max_v == min_v:
            return np.array([0.5] * len(arr))

        return (arr - min_v) / (max_v - min_v)

    # ------------------------------------------------------------------
    # 6) بناء المحفظة
    # ------------------------------------------------------------------
    def build_portfolio(self, capital, max_stocks=12, max_weight_per_stock=0.2):
        print("بدء بناء المحفظة...")
        capital = float(capital)

        # 1) التاريخ السعري
        history = self._get_price_history()
        if not history:
            raise ValueError("لا توجد بيانات تاريخية صالحة لأي سهم من الكون المختار.")

        # 2) عامل العائد/المخاطرة
        rr_df = self._compute_return_risk(history)
        if rr_df.empty:
            raise ValueError("تعذر حساب العائد/المخاطرة للأسهم.")

        # 3) عامل الزخم
        mom_df = self._compute_momentum(history)
        if mom_df.empty:
            raise ValueError("تعذر حساب الزخم السعري للأسهم.")

        # 4) عامل الأساسيات
        fund_scores_dict = self._compute_fundamental_scores()

        # 5) دمج العوامل في جدول واحد
        factor_df = pd.merge(rr_df, mom_df, on="symbol", how="inner")

        if factor_df.empty:
            raise ValueError("لم يتبق أسهم مشتركة بين عوامل العائد/المخاطرة والزخم.")

        factor_df["fund_score_raw"] = factor_df["symbol"].map(
            lambda s: fund_scores_dict.get(s, 0.5)
        )

        # 6) نطبّع كل عامل إلى [0,1]
        factor_df["risk_score"] = self._min_max_normalize(factor_df["risk_score_raw"].values)
        factor_df["mom_score"] = self._min_max_normalize(factor_df["mom_score_raw"].values)
        factor_df["fund_score"] = self._min_max_normalize(factor_df["fund_score_raw"].values)

        # 7) حساب Score النهائي
        factor_df["total_score"] = (
            self.w_risk * factor_df["risk_score"] +
            self.w_fund * factor_df["fund_score"] +
            self.w_mom * factor_df["mom_score"]
        )

        # نعمل sort حسب total_score
        factor_df = factor_df.sort_values("total_score", ascending=False)

        # نخزن نسخة لعرضها في Streamlit
        self.last_factor_df = factor_df.copy().reset_index(drop=True)

        # 8) نختار أعلى max_stocks
        top_df = factor_df.head(max_stocks).copy()
        top_symbols = top_df["symbol"].tolist()

        # 9) تحويل total_score إلى أوزان مبدئية
        raw_scores = np.clip(top_df["total_score"].values, a_min=0.0, a_max=None)
        if raw_scores.sum() == 0:
            weights_raw = np.array([1.0 / len(top_symbols)] * len(top_symbols))
        else:
            weights_raw = raw_scores / raw_scores.sum()

        # تطبيق حد أقصى للوزن
        weights_clipped = np.clip(weights_raw, 0.0, max_weight_per_stock)
        if weights_clipped.sum() == 0:
            weights_clipped = np.array([1.0 / len(top_symbols)] * len(top_symbols))
        else:
            weights_clipped = weights_clipped / weights_clipped.sum()

        # 10) جلب آخر سعر لكل سهم من التاريخ نفسه
        last_prices = {}
        for sym in top_symbols:
            s = history.get(sym)
            if s is None or s.empty:
                continue
            p = float(s.iloc[-1])
            if np.isnan(p):
                continue
            last_prices[sym] = p

        if not last_prices:
            raise ValueError("تعذر الحصول على أسعار نهائية للأسهم المختارة.")

        # 11) مطابقة الأوزان مع الأسهم اللي لها سعر فعلي
        valid_syms = [sym for sym in top_symbols if sym in last_prices]
        if not valid_syms:
            raise ValueError("بعد استبعاد الأسهم بدون سعر، لم يتبق أي سهم لبناء المحفظة.")

        w_final = []
        for sym in valid_syms:
            idx = top_symbols.index(sym)
            w_final.append(weights_clipped[idx])

        w_final = np.array(w_final, dtype=float)
        w_final = w_final / w_final.sum()

        # 12) تحويل الأوزان لعدد أسهم فعلي
        rows = []
        for sym, w in zip(valid_syms, w_final):
            price = last_prices[sym]
            alloc = capital * w
            shares = int(alloc // price)
            mv = shares * price

            rows.append({
                "symbol": sym,
                "weight_target": w,
                "capital_alloc": alloc,
                "last_price": price,
                "shares": shares,
                "market_value": mv
            })

        if not rows:
            raise ValueError("لم يتمكن النظام من تخصيص أي أسهم (ربما الأسعار غير صالحة).")

        pf_df = pd.DataFrame.from_records(rows)
        total_mv = pf_df["market_value"].sum()

        if total_mv > 0:
            pf_df["weight_real"] = pf_df["market_value"] / total_mv
        else:
            pf_df["weight_real"] = 0.0

        pf_df = pf_df.sort_values("weight_real", ascending=False).reset_index(drop=True)

        cash_left = capital - total_mv
        print("تم بناء المحفظة بنجاح!")
        return pf_df, cash_left
