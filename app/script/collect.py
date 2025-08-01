import yfinance as yf
import pandas_ta as ta
import pandas as pd
from app.script.db import SessionLocal
from app.script.models import TechnicalIndicator
from datetime import datetime, timedelta
from app.script.debug import debug_printer as d

CURRENCY_PAIRS = ["USDJPY", "EURUSD", "EURJPY"]  # USD-JPY, USD-EUR, EUR-JPY の3ペアを取得

def fetch_technicals(pair_code, return_rows=1):
    """
    Fetch technical indicators for a given currency pair.
    
    Args:        
        pair_code (str): The currency pair code (e.g., "USDJPY").
        return_rows (int): Number of rows to return (default is 1).
    """
    d.print(f"fetching... ")
    
    # 過去30日間のデータを取得
    end = datetime.today()
    start = end - timedelta(days=30)  
    ticker = pair_code + "=X"
    
    # データフレームの取得とクリーニング
    df = yf.download(ticker, start=start, end=end, interval="1h")
    debug_info = f"Fetched data for {pair_code}: {df.shape[0]} rows, {df.shape[1]} columns"
    d.print(debug_info, level='debug')
    
    # マルチインデックスの列を単一の列に変換
    if isinstance(df.columns, pd.MultiIndex):
        # d.print("Converting MultiIndex columns to simple columns", level='debug')
        df.columns = [col[0] for col in df.columns]  # 最初のレベルのみを使用
        # d.print(f"converted columns: {df.columns.tolist()}", level='debug')
    
    df.to_csv(f"data/{pair_code}_technical_data.csv")

    if df.empty or len(df) < 50:
        d.print(f"⚠️ Data too short or empty for {pair_code}, shape: {df.shape}", level='warning')
        return pd.DataFrame()  # 空のDataFrameを返す
    
    # データの最初と最後の日付をログ
    # d.print(f"Data range for {pair_code}: {df.index[0]} to {df.index[-1]}", level='debug')

    # 1. RSI（Relative Strength Index）相対力指数
    df["rsi"] = ta.rsi(df["Close"], length=14)

    # 2. MACD（Moving Average Convergence Divergence）移動平均収束発散法
    macd = ta.macd(df["Close"])
    if macd is not None and "MACD_12_26_9" in macd and "MACDs_12_26_9" in macd:
        df["macd"] = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
    else:
        d.print(f"⚠️ MACD calculation failed for {pair_code}", level='warning')
        df["macd"] = df["macd_signal"] = None

    # 3. SMA（Simple Moving Average）単純移動平均
    df["sma_20"] = ta.sma(df["Close"], length=20)
    
    # 4. EMA（Exponential Moving Average）指数移動平均
    df["ema_50"] = ta.ema(df["Close"], length=50)

    # 5. Bollinger Bands ボリンジャーバンド
    bb = ta.bbands(df["Close"])
    if bb is not None:
        df["bb_upper"] = bb.get("BBU_20_2.0", None)
        df["bb_lower"] = bb.get("BBL_20_2.0", None)
    else:
        df["bb_upper"] = df["bb_lower"] = None

    # 6. ADX（Average Directional Index）平均方向性指数
    adx = ta.adx(df["High"], df["Low"], df["Close"])
    df["adx"] = adx["ADX_14"] if adx is not None and "ADX_14" in adx else None

    return df.tail(return_rows)  # 指定の行数だけを返す（デフォルト1）

def collect_technical_data():
    session = SessionLocal()
    
    d.print_ts(f"<<< scheduled task: collect_technical_data >>>", level='debug')
    
    try:
        for pair in CURRENCY_PAIRS:
            d.print(f"{pair})", level='debug')
            # APIでデータ取得・テクニカル指標計算
            df = fetch_technicals(pair, return_rows=1)
            
            if df.empty:
                d.print(f"Skipping {pair} due to empty dataframe", level='error')
                continue
            
            # d.print(f"{df.tail(1)}", level='debug')
            df.tail(1).to_csv(f"data/{pair}_technical.csv", index=True)
            
                
            for _, row in df.iterrows():
                timestamp = row.name.to_pydatetime()
                # データベースに保存する前に、すでに存在するか確認
                exists = session.query(TechnicalIndicator).filter_by(
                    currency_pair=pair, timestamp=timestamp
                ).first()
                # 存在するならスキップ
                if exists:
                    d.print(f"⏩ Skip: {pair} @ {timestamp}")
                    continue
                    
                # スカラー値を使用するように修正
                ti = TechnicalIndicator(
                    currency_pair=pair,
                    timestamp=timestamp,
                    close=None if pd.isna(row["Close"]) else float(row["Close"]),
                    rsi=None if pd.isna(row["rsi"]) else float(row["rsi"]),
                    macd=None if pd.isna(row["macd"]) else float(row["macd"]),
                    macd_signal=None if pd.isna(row["macd_signal"]) else float(row["macd_signal"]),
                    sma_20=None if pd.isna(row["sma_20"]) else float(row["sma_20"]),
                    ema_50=None if pd.isna(row["ema_50"]) else float(row["ema_50"]),
                    bb_upper=None if pd.isna(row["bb_upper"]) else float(row["bb_upper"]),
                    bb_lower=None if pd.isna(row["bb_lower"]) else float(row["bb_lower"]),
                    adx=None if pd.isna(row["adx"]) else float(row["adx"])
                )
                session.add(ti)
                d.print(f"✅ Added: {pair} @ {timestamp}")
                
                
                
        session.commit()
    except Exception as e:
        d.print(f"Error in collect_technical_data: {str(e)}", level='error')
        session.rollback()
    finally:
        session.close()