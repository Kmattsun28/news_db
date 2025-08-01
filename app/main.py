from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response, HTMLResponse
from app.scheduler import start_scheduler
from app.script.db import SessionLocal
from app.script.models import TechnicalIndicator, NewsArticle
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import io
from typing import Optional, List
from sqlalchemy import desc
from app.script.debug import debug_printer as d
from app.ws_trump import run_ws
import threading

app = FastAPI()

@app.on_event("startup")
def startup_event():
    start_scheduler()
    threading.Thread(target=run_ws, daemon=True).start()

@app.get("/")
def read_root():
    return {"message": "Forex Technical Indicator API is running"}

# ============ テクニカル指標 ============

@app.get("/visualization/{pair_code}")
def visualize_indicators(
    pair_code: str,
    days: int = Query(default=7, ge=1, le=30),
    width: int = Query(default=1000, ge=300, le=2000),
    height: int = Query(default=800, ge=200, le=1600),
    indicators: List[str] = Query(default=["close", "rsi", "macd", "macd_signal", "sma_20", "ema_50", "bb_upper", "bb_lower", "adx"])
):
    """
    為替レートとテクニカル指標のグラフを生成します。
    
    Args:
        pair_code: 通貨ペアコード (例: "USDJPY", "EURJPY")
        days: 何日分のデータを表示するか (1-30日)
        indicators: 表示する指標のリスト
    """
    # データベースからデータを取得
    session = SessionLocal()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.currency_pair == pair_code,
            TechnicalIndicator.timestamp >= start_date,
            TechnicalIndicator.timestamp <= end_date
        ).order_by(TechnicalIndicator.timestamp)
        
        results = query.all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"データが見つかりません。通貨ペア: {pair_code}")
        
        # DataFrameに変換
        data = {
            'timestamp': [r.timestamp for r in results],
            'close': [r.close for r in results],
            'rsi': [r.rsi for r in results],
            'macd': [r.macd for r in results],
            'macd_signal': [r.macd_signal for r in results],
            'sma_20': [r.sma_20 for r in results],
            'ema_50': [r.ema_50 for r in results],
            'bb_upper': [r.bb_upper for r in results],
            'bb_lower': [r.bb_lower for r in results],
            'adx': [r.adx for r in results]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        # グラフ作成
        plt.figure(figsize=(12, 8))
        
        # figureサイズを動的に設定
        fig_width = width / 100  # ピクセルからインチへ変換
        fig_height = height / 100
        
        # サブプロットの設定
        fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(fig_width, fig_height), 
                            sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # メインチャート（価格とMA）
        price_indicators = [i for i in ["close", "sma_20", "ema_50", "bb_upper", "bb_lower"] if i in indicators]
        for ind in price_indicators:
            if ind == "close":
                axes[0].plot(df.index, df[ind], label=f"価格", linewidth=1.5)
            else:
                axes[0].plot(df.index, df[ind], label=f"{ind}", linewidth=1)
        
        axes[0].set_title(f"{pair_code} テクニカル分析 ({days}日間)")
        axes[0].set_ylabel("価格")
        axes[0].legend()
        axes[0].grid(True)
        
        # RSI
        if "rsi" in indicators:
            axes[1].plot(df.index, df["rsi"], label="RSI", color="purple")
            axes[1].axhline(y=70, color='r', linestyle='-', alpha=0.3)
            axes[1].axhline(y=30, color='g', linestyle='-', alpha=0.3)
            axes[1].set_ylabel("RSI")
            axes[1].set_ylim([0, 100])
            axes[1].legend()
            axes[1].grid(True)
        
        # MACD
        if "macd" in indicators and "macd_signal" in indicators:
            axes[2].plot(df.index, df["macd"], label="MACD")
            axes[2].plot(df.index, df["macd_signal"], label="シグナル", linestyle="--")
            axes[2].bar(df.index, df["macd"] - df["macd_signal"], color=["green" if val >= 0 else "red" for val in (df["macd"] - df["macd_signal"])], alpha=0.3)
            axes[2].set_ylabel("MACD")
            axes[2].legend()
            axes[2].grid(True)
        
        plt.tight_layout()
        
        # 画像をバイト列に変換
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        
        return Response(content=buf.getvalue(), media_type="image/png")
    
    finally:
        session.close()

# HTMLでグラフを表示するページ
@app.get("/chart/{pair_code}", response_class=HTMLResponse)
def show_chart(
    pair_code: str,
    days: int = Query(default=7, ge=1, le=30)
):
    """
    為替レートとテクニカル指標のHTMLページを返します。
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>{pair_code} テクニカル分析</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #333; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .chart {{ width: 100%; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .controls {{ margin-bottom: 20px; }}
                button {{ padding: 8px 16px; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{pair_code} テクニカル分析</h1>
                <div class="controls">
                    <button onclick="updateDays(1)">1日</button>
                    <button onclick="updateDays(7)">1週間</button>
                    <button onclick="updateDays(14)">2週間</button>
                    <button onclick="updateDays(30)">1ヶ月</button>
                </div>
                <img class="chart" src="/visualization/{pair_code}?days={days}" alt="{pair_code} Chart">
            </div>
            <script>
                function updateDays(days) {{
                    window.location.href = `/chart/{pair_code}?days=` + days;
                }}
            </script>
        </body>
    </html>
    """
    return html_content

# 複数通貨ペアの比較ページ
@app.get("/compare", response_class=HTMLResponse)
def compare_pairs(
    days: int = Query(default=7, ge=1, le=30),
    pairs: List[str] = Query(default=["USDJPY", "EURJPY"])
):
    """
    複数の通貨ペアを比較するHTMLページを返します。
    """
    # 利用可能な通貨ペアリスト
    available_pairs = ["USDJPY", "EURJPY"]
    
    # 修正1: 表示する通貨ペアの数に応じてサイズを調整（値を小さめに設定）
    chart_width = 600 if len(pairs) > 1 else 1000
    chart_height = 500 if len(pairs) > 1 else 800
    
    # HTML生成
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>為替テクニカル分析 比較</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1 {{ color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                
                /* チャートコンテナのスタイル改善 */
                .chart-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
                    gap: 20px;
                    justify-content: center;
                }}
                
                /* チャートボックスのスタイル改善 */
                .chart-box {{
                    width: 100%;
                    margin-bottom: 20px;
                    overflow: hidden;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    border-radius: 5px;
                    padding: 10px;
                }}
                
                /* チャートイメージのスタイル改善 */
                .chart {{
                    width: 100%;
                    height: auto;
                    display: block;
                    max-width: 100%;
                }}
                
                .controls {{ margin-bottom: 20px; background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                button {{ padding: 8px 16px; margin-right: 10px; cursor: pointer; }}
                button.active {{ background: #4CAF50; color: white; }}
                .checkbox-group {{ margin: 10px 0; }}
                label {{ margin-right: 15px; cursor: pointer; }}
                h2, h3 {{ margin-top: 0; color: #555; text-align: center; }}
                .refresh {{ float: right; padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                .refresh:hover {{ background: #0b7dda; }}
                
                /* 適用ボタン追加 */
                .apply-btn {{
                    margin-left: 15px;
                    background: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 15px;
                    cursor: pointer;
                }}
                
                /* レスポンシブ対応強化 */
                @media (max-width: 768px) {{
                    .chart-container {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>為替テクニカル分析 比較</h1>
                
                <div class="controls">
                    <button id="refreshBtn" class="refresh" onclick="refreshAllCharts()">更新</button>
                    <h2>表示設定</h2>
                    
                    <div>
                        <strong>期間:</strong>
                        <button onclick="updateDays(1)" class="{{'active' if days == 1 else ''}}">1日</button>
                        <button onclick="updateDays(7)" class="{{'active' if days == 7 else ''}}">1週間</button>
                        <button onclick="updateDays(14)" class="{{'active' if days == 14 else ''}}">2週間</button>
                        <button onclick="updateDays(30)" class="{{'active' if days == 30 else ''}}">1ヶ月</button>
                    </div>
                    
                    <div class="checkbox-group">
                        <strong>通貨ペア:</strong>
                        {''.join([f'<label><input type="checkbox" name="pair" value="{pair}" {"checked" if pair in pairs else ""}> {pair}</label>' for pair in available_pairs])}
                        <button class="apply-btn" onclick="updatePairs()">適用</button>
                    </div>
                </div>
                
                <div class="chart-container">
                    {''.join([f'<div class="chart-box"><h3>{pair}</h3><img class="chart" src="/visualization/{pair}?days={days}&width={chart_width}&height={chart_height}" alt="{pair} Chart"></div>' for pair in pairs])}
                </div>
            </div>
            
            <script>
                function updateDays(days) {{
                    const url = new URL(window.location);
                    url.searchParams.set('days', days);
                    const checkedPairs = Array.from(document.querySelectorAll('input[name="pair"]:checked')).map(el => el.value);
                    if (checkedPairs.length > 0) {{
                        url.searchParams.delete('pairs');
                        checkedPairs.forEach(pair => url.searchParams.append('pairs', pair));
                    }}
                    window.location.href = url.toString();
                }}
                
                function updatePairs() {{
                    const url = new URL(window.location);
                    const checkedPairs = Array.from(document.querySelectorAll('input[name="pair"]:checked')).map(el => el.value);
                    if (checkedPairs.length > 0) {{
                        url.searchParams.delete('pairs');
                        checkedPairs.forEach(pair => url.searchParams.append('pairs', pair));
                        window.location.href = url.toString();
                    }} else {{
                        alert('少なくとも1つの通貨ペアを選択してください');
                    }}
                }}
                
                function refreshAllCharts() {{
                    const charts = document.querySelectorAll('.chart');
                    const timestamp = new Date().getTime();
                    charts.forEach(chart => {{
                        chart.src = chart.src.split('&refresh=')[0] + '&refresh=' + timestamp;
                    }});
                }}
            </script>
        </body>
    </html>
    """
    return html_content

# 指標のデータをJSON形式で取得するAPI
@app.get("/api/indicators/{pair_code}")
def get_indicators(
    pair_code: str,
    days: int = Query(default=7, ge=1, le=30)
):
    """
    通貨ペアのテクニカル指標データをJSON形式で返します。
    """
    session = SessionLocal()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.currency_pair == pair_code,
            TechnicalIndicator.timestamp >= start_date,
            TechnicalIndicator.timestamp <= end_date
        ).order_by(TechnicalIndicator.timestamp)
        
        results = query.all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"データが見つかりません。通貨ペア: {pair_code}")
        
        # JSONに変換可能なデータ形式に変換
        indicators = []
        for r in results:
            indicators.append({
                'timestamp': r.timestamp.isoformat(),
                'close': r.close,
                'rsi': r.rsi,
                'macd': r.macd,
                'macd_signal': r.macd_signal,
                'sma_20': r.sma_20,
                'ema_50': r.ema_50,
                'bb_upper': r.bb_upper,
                'bb_lower': r.bb_lower,
                'adx': r.adx
            })
        
        return indicators
    
    finally:
        session.close()
        
@app.get("/api/signal_data/{pair_code}")
def get_signal_data(pair_code: str, days: int = 3):
    """
    テクニカル指標と直近ニュースをAIプロンプト用にまとめて返す
    """
    session= SessionLocal()
    try:
        # 最新のテクニカル指標を取得
        indicator = session.query(TechnicalIndicator)\
            .filter(TechnicalIndicator.currency_pair == pair_code)\
            .order_by(TechnicalIndicator.timestamp.desc())\
            .first()
        if not indicator:
            raise HTTPException(status_code=404, detail="テクニカル指標が見つかりません")

        # 直近days日分のニュース記事を取得
        since = datetime.now() - timedelta(days=days)
        news = session.query(NewsArticle)\
            .filter(NewsArticle.published >= since)\
            .order_by(NewsArticle.published.desc())\
            .all()

        # AIプロンプト用の辞書形式で返す
        return {
            "technical": {
                "currency_pair": indicator.currency_pair,
                "timestamp": indicator.timestamp.isoformat(),
                "close": indicator.close,
                "rsi": indicator.rsi,
                "macd": indicator.macd,
                "macd_signal": indicator.macd_signal,
                "sma_20": indicator.sma_20,
                "ema_50": indicator.ema_50,
                "bb_upper": indicator.bb_upper,
                "bb_lower": indicator.bb_lower,
                "adx": indicator.adx,
            },
            "news": [
                {
                    "title": n.title,
                    "summary": n.summary,
                    "url": n.url,
                    "published": n.published.isoformat() if n.published else None,
                    "category": n.category
                }
                for n in news
            ]
        }
    finally:
        session.close()
        
from transformers import AutoModelForCausalLM, AutoTokenizer
@app.get("/api/qwen_signal/{pair_code}")
def qwen_signal(pair_code: str, days: int = 10):
    """
    テクニカル指標の推移と直近ニュースをAIプロンプト用にまとめ、Qwenで推論した「買い/売り」判断と信頼度を返す
    """
    d.print_ts(f"<<< API: qwen_signal >>> pair_code={pair_code}, days={days}", level='error')
    session = SessionLocal()
    try:
        # 指定期間のテクニカル指標を全件取得
        since = datetime.now() - timedelta(days=days)
        indicators = session.query(TechnicalIndicator)\
            .filter(TechnicalIndicator.currency_pair == pair_code)\
            .filter(TechnicalIndicator.timestamp >= since)\
            .order_by(TechnicalIndicator.timestamp.asc())\
            .all()
        if not indicators:
            raise HTTPException(status_code=404, detail="テクニカル指標が見つかりません")
        
        d.print(f"取得したテクニカル指標の件数: {len(indicators)}", level='error')

        # 直近days日分のニュース記事を取得
        news = session.query(NewsArticle)\
            .filter(NewsArticle.published >= since)\
            .order_by(NewsArticle.published.desc())\
            .all()
    finally:
        session.close()

    # テクニカル指標の推移をリスト形式で整形
    technical_history = [
        {
            "timestamp": r.timestamp.isoformat(),
            "close": r.close,
            "rsi": r.rsi,
            "macd": r.macd,
            "macd_signal": r.macd_signal,
            "sma_20": r.sma_20,
            "ema_50": r.ema_50,
            "bb_upper": r.bb_upper,
            "bb_lower": r.bb_lower,
            "adx": r.adx,
        }
        for r in indicators
    ]

    # プロンプト生成
    # プロンプト生成部分を修正
    prompt = (
        "あなたは為替トレーダーAIです。\n"
        "以下のテクニカル指標の推移と直近ニュースを参考に、通貨ペアの「買い」「売り」判断とその信頼度（0.0～1.0）を日本語で簡潔に出力してください。\n\n"
        "【テクニカル指標の推移】\n"
    )

    # テクニカル指標のヘッダー
    prompt += "日時,終値,RSI,MACD,シグナル,SMA20,EMA50,BBup,BBlow,ADX\n"

    # 各行のデータ
    for r in technical_history:
        prompt += f"{r['timestamp']},{r['close']},{r['rsi']},{r['macd']},{r['macd_signal']},{r['sma_20']},{r['ema_50']},{r['bb_upper']},{r['bb_lower']},{r['adx']}\n"

    prompt += "\n【ニュース要約】\n"
    
    for n in news:
        prompt += f"- {n.published.isoformat() if n.published else ''} {n.title} : {n.summary}\n"
        
    prompt += "\n出力例: 買い 0.85\n"

    d.print(f"Qwenプロンプト: \n{prompt}", output_path="/app/data/qwen_signal.log")

    # Qwenモデルで推論
    model_name = "Qwen/Qwen3-8B"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto"
    )
    messages = [
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=32768,
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    try:
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0
    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    d.print(f"出力: \n{thinking_content}\n {content}\n", output_path="/app/data/qwen_signal.log")
    
    return {
        "pair_code": pair_code,
        "prompt": prompt,
        "thinking_content": thinking_content,
        "content": content
    }
    
    

from fastapi import FastAPI, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

# 個々のニュース記事用のモデル
class NewsArticleResponse(BaseModel):
    id: int
    category: str
    title: str
    summary: str
    url: str
    published: datetime
    currency_tags: List[str]  # 追加

    class Config:
        orm_mode = True

# 日時検索結果全体を表すモデル（追加）
class NewsAtTimeResponse(BaseModel):
    total: int
    end_date: str
    start_date: str
    currency_filter: Optional[List[str]] = None
    articles: List[NewsArticleResponse]

    class Config:
        orm_mode = True

# 日時を指定してニュース記事を取得するAPI
@app.get("/api/news/at", response_model=NewsAtTimeResponse)  # ここをNewsAtTimeResponseに変更
def get_news_at_time(
    date_time: str = Query(..., description="基準日時（ISO形式、例: 2025-07-04T15:30:00）"),
    hours_back: int = Query(24, ge=1, le=72, description="遡る時間（時間単位）"),
    category: Optional[str] = Query(None, description="カテゴリでフィルタ"),
    currencies: List[str] = Query(default=[], description="通貨フィルタ（複数選択可、例: USD,EUR,JPY）"),
    limit: int = Query(100, ge=1, le=500, description="最大取得件数")
):
    """
    指定した日時より前の一定時間以内のニュース記事を取得します。
    例：2025-07-04T15:30:00を指定し、hours_back=24とすると、
    2025-07-03T15:30:00から2025-07-04T15:30:00までのニュースが取得されます。
    
    通貨フィルタ例（完全一致のみ）:
    - currencies=USD (USDのみの記事)
    - currencies=USD&currencies=JPY (USDとJPYの両方のみを含む記事)
    - currencies=EUR (EURのみの記事)
    
    注意: 指定した通貨以外が含まれている記事は除外されます。
    例: USD,JPYを指定した場合、USD,JPY,EURのような記事は取得されません。
    """
    session = SessionLocal()
    try:
        # 文字列をdatetimeに変換
        try:
            end_date = datetime.fromisoformat(date_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="日時形式が無効です。ISO形式で指定してください（例: 2025-07-04T15:30:00）")
        
        # 開始日時を計算
        start_date = end_date - timedelta(hours=hours_back)
        
        # クエリ構築
        query = session.query(NewsArticle).filter(
            NewsArticle.published >= start_date,
            NewsArticle.published <= end_date
        )
        
        # カテゴリフィルタ
        if category:
            query = query.filter(NewsArticle.category == category)
        
        # 通貨フィルタ（完全一致のみ）
        if currencies:
            # 有効な通貨コードのみを受け入れ
            valid_currencies = ["USD", "EUR", "JPY"]
            filtered_currencies = [c.upper() for c in currencies if c.upper() in valid_currencies]
            
            if filtered_currencies:
                # JSON配列内に指定された通貨のみが含まれている記事を検索（完全一致）
                from sqlalchemy import and_, func, text
                
                # 1. 配列の長さが指定された通currency数と一致すること
                array_length_condition = text(f"json_array_length(news_articles.currency_tags) = {len(filtered_currencies)}")
                
                # 2. 指定されたすべての通貨が含まれていること
                currency_conditions = []
                for currency in filtered_currencies:
                    currency_conditions.append(
                        text(f"EXISTS (SELECT 1 FROM json_each(news_articles.currency_tags) WHERE value = '{currency}')")
                    )
                # 両方の条件を満たす記事のみを取得
                query = query.filter(and_(array_length_condition, *currency_conditions))
            
        # 日時の降順で並べ替え
        query = query.order_by(desc(NewsArticle.published))
        
        # 結果の取得
        total_count = query.count()
        news_articles = query.limit(limit).all()
        
        # レスポンス作成（フィルタ情報も含める）
        return {
            "total": total_count,
            "end_date": end_date.isoformat(),
            "start_date": start_date.isoformat(),
            "currency_filter": currencies if currencies else None,
            "articles": news_articles
        }
    finally:
        session.close()