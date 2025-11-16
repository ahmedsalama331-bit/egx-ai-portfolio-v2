import numpy as np
import pandas as pd
from egx_yahoo import EGXYahoo

class SmartAIPortfolioBuilder:
    """
    ذكاء اصطناعي مبسط لكن حقيقي:
    - لكل سهم: نحصل على السلسلة التاريخية للأسعار
    - نحسب العائد اليومي → العائد السنوي
    - نحسب التذبذب السنوي (volatility)
    - نحسب Score = return / volatility
    - نختار أفضل الأسهم ونحوّل الأوزان إلى عدد أسهم فعلي
    """

    def __init__(self, universe, lookback_days=180, auto_suffix=True, verbose=True):
        self.universe = list(universe)
        self.lookback_days = lookback_days
        self.egx = EGXYahoo(self.universe, auto_suffix=auto_suffix, verbose=verbose)
        self.verbose = verbose

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def _get_price_history(self):
        """
        نجيب تاريخ الأسعار لكل سهم باستخدام get_price لكل سهم مستقلاً.
        نرجع dict بالشكل:
        {
            "COMI": Series,
            "ETEL": Series,
            ...
        }
        """
        history = {}

        for sym in self.universe:
            s = self.egx.get_price(sym)
            if s is None or s.empty:
                self._log(f"⚠️ لا توجد بيانات تاريخية للسهم: {sym}")
                continue

            # ناخد آخر lookback_days فقط
            if len(s) > self.lookback_days:
                s = s.iloc[-self.lookback_days:]

            s = s.dropna()
            if len(s) < 2:
                self._log(f"⚠️ عدد نقاط الأسعار قليل جداً للسهم: {sym}")
                continue

            history[sym] = s

        return history

    def _compute_features(self, history_dict):
        """
        نحسب لكل سهم:
        - annual_return
        - annual_vol
        نرجع dict بالشكل:
        {
            "COMI": {"annual_return": ..., "annual_vol": ...},
            ...
        }
        """
        features = {}

        for sym, s in history_dict.items():
            # عوائد يومية
            daily_ret = s.pct_change().dropna()
            if daily_ret.empty:
                continue

            mean_daily = float(daily_ret.mean())
            daily_vol = float(daily_ret.std())

            annual_return = (1 + mean_daily) ** 250 - 1
            annual_vol = daily_vol * np.sqrt(250)

            if np.isnan(annual_return) or np.isnan(annual_vol) or annual_vol == 0:
                continue

            features[sym] = {
                "annual_return": annual_return,
                "annual_vol": annual_vol,
            }

        return features

    def build_portfolio(self, capital, max_stocks=12, max_weight_per_stock=0.2):
        """
        يبني المحفظة بناءً على:
        - أعلى Score (return / volatility)
        - حد أقصى لعدد الأسهم
        - حد أقصى لوزن السهم الواحد
        كما يقوم بحفظ جدول يوضح:
        - العائد السنوي
        - التذبذب السنوي
        - Score
        في self.last_features_df لعرضه في Streamlit.
        """
        capital = float(capital)

        # 1) جلب التاريخ السعري لكل سهم
        history = self._get_price_history()
        if not history:
            raise ValueError("لا توجد بيانات تاريخية صالحة لأي سهم من الكون المختار.")

        # 2) حساب العائد/المخاطرة لكل سهم (dict)
        features_dict = self._compute_features(history)
        if not features_dict:
            raise ValueError("لا يمكن حساب العائد/المخاطرة للأسهم بعد التنظيف.")

        # 3) تحويل الـ dict إلى DataFrame آمن (بدون Scalars)
        #    index = symbol, columns = annual_return, annual_vol
        features_df = pd.DataFrame.from_dict(features_dict, orient="index")

        # 4) حساب Score لكل سهم
        eps = 1e-6
        features_df["score"] = features_df["annual_return"] / (features_df["annual_vol"] + eps)
        features_df = features_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["score"])

        if features_df.empty:
            raise ValueError("لا يمكن حساب Score صالح لأي سهم.")

        # 5) ترتيب الأسهم حسب Score تنازلياً
        features_df = features_df.sort_values("score", ascending=False)

        # 6) حفظ نسخة من التحليل لعرضها في Streamlit لاحقاً
        #    reset_index → يصبح لدينا عمود 'symbol'
        self.last_features_df = (
            features_df
            .reset_index()
            .rename(columns={"index": "symbol"})
        )

        # 7) اختيار أفضل max_stocks
        top_df = features_df.head(max_stocks)
        top_symbols = top_df.index.tolist()

        # 8) تحويل Scores الأعلى إلى أوزان أولية
        raw_scores = np.clip(top_df["score"].values.astype(float), a_min=0.0, a_max=None)

        if raw_scores.sum() == 0:
            # لو كل السكورز <= 0 → توزيع متساوي
            weights_raw = np.array([1.0 / len(top_symbols)] * len(top_symbols))
        else:
            weights_raw = raw_scores / raw_scores.sum()

        # 9) تطبيق حد أقصى لوزن السهم الواحد
        weights_clipped = np.clip(weights_raw, 0.0, max_weight_per_stock)
        if weights_clipped.sum() == 0:
            weights_clipped = np.array([1.0 / len(top_symbols)] * len(top_symbols))
        else:
            weights_clipped = weights_clipped / weights_clipped.sum()

        # 10) آخر سعر لكل سهم من التاريخ الذي لدينا بالفعل
        last_prices = {}
        for sym in top_symbols:
            s = history.get(sym)
            if s is None or s.empty:
                continue
            last_price = float(s.iloc[-1])
            if np.isnan(last_price):
                continue
            last_prices[sym] = last_price

        if not last_prices:
            raise ValueError("لا توجد أسعار حالية في السلاسل التاريخية المختارة.")

        # 11) نطابق الأوزان مع الأسهم اللي لها سعر فعلي
        filtered_syms = [sym for sym in top_symbols if sym in last_prices]
        if not filtered_syms:
            raise ValueError("بعد استبعاد الأسهم بدون سعر فعلي، لم يتبق أي سهم لبناء المحفظة.")

        # إعادة ضبط الأوزان لنفس ترتيب filtered_syms
        weights_for_filtered = []
        for sym in filtered_syms:
            idx = top_symbols.index(sym)
            weights_for_filtered.append(weights_clipped[idx])

        weights_for_filtered = np.array(weights_for_filtered, dtype=float)
        weights_for_filtered = weights_for_filtered / weights_for_filtered.sum()

        # 12) تحويل الأوزان إلى عدد أسهم فعلي
        rows = []
        for sym, w in zip(filtered_syms, weights_for_filtered):
            price = last_prices[sym]
            alloc = capital * w
            shares = int(alloc // price)
            market_value = shares * price

            rows.append({
                "symbol": sym,
                "weight_target": w,
                "capital_alloc": alloc,
                "last_price": price,
                "shares": shares,
                "market_value": market_value,
            })

        if not rows:
            raise ValueError("لم يتمكن النظام من تخصيص أي أسهم (ربما الأسعار غير صالحة).")

        df = pd.DataFrame.from_records(rows)

        total_mv = df["market_value"].sum()
        if total_mv > 0:
            df["weight_real"] = df["market_value"] / total_mv
        else:
            df["weight_real"] = 0.0

        df = df.sort_values("weight_real", ascending=False).reset_index(drop=True)

        cash_left = capital - total_mv
        return df, cash_left
