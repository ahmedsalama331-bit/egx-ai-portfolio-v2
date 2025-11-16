import yfinance as yf
import pandas as pd

class EGXYahoo:
    def __init__(self, tickers, auto_suffix=True, verbose=True):
        """
        tickers: قائمة رموز EGX (مثلاً: ["COMI", "EKHO", "AMOC"])
        auto_suffix: لو True يضيف .CA تلقائيًا لو مش موجودة
        """
        self.tickers = tickers
        self.auto_suffix = auto_suffix
        self.verbose = verbose

    def _log(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def _format_symbol(self, symbol):
        sym = str(symbol).strip().upper()
        if self.auto_suffix and not sym.endswith(".CA"):
            sym = sym + ".CA"
        return sym

    def get_price(self, symbol, start=None, end=None, adjusted=False):
        """
        يرجّع Series فيها أسعار الإغلاق لسهم واحد
        """
        sym = self._format_symbol(symbol)

        try:
            data = yf.download(
                sym,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=adjusted,
                progress=False,
            )

            if data.empty:
                self._log(f"⚠️ لا توجد بيانات للسهم: {sym}")
                return None

            data = data.sort_index()
            close_series = data["Close"].copy()
            close_series.name = sym
            return close_series
        except Exception as e:
            self._log(f"❌ حدث خطأ أثناء تحميل البيانات للسهم {sym}: {e}")
            return None

    def get_all(self, start=None, end=None, adjusted=False):
        """
        يرجّع DataFrame لأسعار الإغلاق لكل الأسهم في self.tickers
        """
        prices = {}

        for sym in self.tickers:
            self._log("Downloading:", sym)
            s = self.get_price(sym, start=start, end=end, adjusted=adjusted)
            if s is None or s.empty:
                self._log(f"⚠️ No data for {sym}, skipping.")
                continue
            prices[self._format_symbol(sym)] = s

        if not prices:
            return pd.DataFrame()

        df = pd.DataFrame(prices)
        df = df.sort_index()
        return df

    def get_last_price(self, symbol, adjusted=False):
        """
        يرجّع آخر سعر إغلاق للسهم (float) أو None لو مفيش بيانات
        """
        s = self.get_price(symbol, adjusted=adjusted)
        if s is None or s.empty:
            return None
        return float(s.iloc[-1])
