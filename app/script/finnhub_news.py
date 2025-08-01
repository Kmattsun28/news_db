import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.script.db import SessionLocal
from app.script.models import NewsArticle
from app.script.debug import debug_printer as d
from app.script.summarizer import summarize_text
from app.script.utils_scraper import detect_currency_tags

class FinnhubNewsCollector:
    """
    Finnhub API を使用して為替市場のニュースを収集するクラス
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Finnhub APIキー（環境変数 FINNHUB_API_KEY からも取得可能）
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("Finnhub APIキーが設定されていません。FINNHUB_API_KEY環境変数を設定するか、api_keyパラメータを指定してください。")
        
        self.base_url = "https://finnhub.io/api/v1"
        self.session = requests.Session()
        
        # 為替関連のカテゴリ設定
        self.forex_categories = ["forex", "general"]
        
        d.print(f"Finnhub News Collector initialized with API key: {self.api_key[:8]}...", level="info")
    
    def get_market_news(self, category: str = "forex", limit: int = 50, minutes_back: int = 30) -> List[Dict]:
        """
        Finnhub APIから市場ニュースを取得（時間範囲指定対応）
        
        Args:
            category: ニュースカテゴリ ("forex", "general" など)
            limit: 取得するニュース数の上限
            minutes_back: 何分前までのニュースを取得するか
            
        Returns:
            ニュース記事のリスト
        """
        from datetime import datetime, timedelta
        import time
        
        # 現在時刻と指定分前の時刻をUnixタイムスタンプで計算
        now = datetime.now()
        past_time = now - timedelta(minutes=minutes_back)
        
        from_timestamp = int(past_time.timestamp())
        to_timestamp = int(now.timestamp())
        
        url = f"{self.base_url}/news"
        params = {
            "category": category,
            "token": self.api_key,
            "from": from_timestamp,
            "to": to_timestamp
        }
        
        try:
            d.print(f"Fetching {category} news from Finnhub API (last {minutes_back} minutes)...", level="debug")
            d.print(f"Time range: {past_time.strftime('%Y-%m-%d %H:%M:%S')} to {now.strftime('%Y-%m-%d %H:%M:%S')}", level="debug")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            news_data = response.json()
            
            if not isinstance(news_data, list):
                d.print(f"Unexpected response format from Finnhub API: {type(news_data)}", level="error")
                return []
            
            # 時間範囲内のニュースを追加フィルタリング（APIの仕様により念のため）
            filtered_news = []
            for article in news_data:
                article_time = article.get("datetime", 0)
                if from_timestamp <= article_time <= to_timestamp:
                    filtered_news.append(article)
            
            # limitで制限
            limited_news = filtered_news[:limit] if len(filtered_news) > limit else filtered_news
            
            d.print(f"Retrieved {len(limited_news)} {category} news articles (from {len(news_data)} total)", level="info")
            return limited_news
            
        except requests.exceptions.RequestException as e:
            d.print(f"Finnhub API request failed: {e}", level="error")
            return []
        except Exception as e:
            d.print(f"Unexpected error fetching Finnhub news: {e}", level="error")
            return []
    
    currency_keywords = [
        # USD関連
        "USD", "US Dollar", "Dollar", "米ドル", "ドル", "Greenback",
        # EUR関連
        "EUR", "Euro", "ユーロ", "欧州通貨",
        # JPY関連
        "JPY", "Japanese Yen", "Yen", "日本円", "円",
        # 中央銀行・政策
        "Bank of Japan", "BOJ", "日銀", "日本銀行",
        "Federal Reserve", "FRB", "Fed", "米連邦準備制度理事会",
        "European Central Bank", "ECB", "欧州中央銀行",
        # その他
        "FX", "Foreign Exchange", "為替", "為替相場", "FOMC", "金融政策"
    ]

    usd_sources = [
        "CNBC", "Bloomberg", "Reuters", "Wall Street Journal", "MarketWatch", "Forexlive", "Yahoo Finance", "Business Insider", "Forbes", "NY Times", "AP", "Fox Business", "CNN", "Barron's", "Motley Fool", "Seeking Alpha", "US Treasury", "Federal Reserve", "WSJ", "USA Today", "TheStreet", "Investopedia", "Kiplinger", "Morningstar", "S&P Global", "Nasdaq", "Zacks", "The Economist", "Politico", "Fortune", "US News", "ABC News", "CBS News", "NBC News", "NPR"
    ]
    eur_sources = [
        "Financial Times", "Handelsblatt", "Le Monde", "Reuters", "Bloomberg", "ECB", "The Guardian", "BBC", "DW", "El País", "Il Sole 24 Ore", "Les Echos", "Frankfurter Allgemeine", "Euronews", "Swissinfo", "RTE",
        "Süddeutsche Zeitung", "La Stampa", "La Repubblica", "Die Welt", "Le Figaro", "Der Spiegel", "Politico Europe", "De Tijd", "NRC Handelsblad", "Het Financieele Dagblad", "Børsen", "Dagens Nyheter", "Svenska Dagbladet", "Aftenposten", "Helsingin Sanomat", "Público", "Expresso", "Kathimerini", "Cyprus Mail", "Irish Times", "Irish Independent", "The Times", "The Telegraph", "Sky News", "L'Express", "Ouest-France", "Trouw", "Volkskrant", "VRT NWS", "NOS", "RTL Nieuws", "Le Soir", "La Libre Belgique"
    ]
    jpy_sources = [
        "Nikkei", "NHK", "日経", "朝日新聞", "読売新聞", "日本経済新聞", "BOJ", "毎日新聞", "共同通信", "Bloomberg Japan", "Reuters Japan", "東洋経済", "産経新聞", "時事通信", "Yahoo!ニュース"
    ]
    usd_countries = ["United States", "US", "America", "米国", "USA"]
    eur_countries = ["Europe", "EU", "Eurozone", "Germany", "France", "欧州", "ユーロ圏", "ドイツ", "フランス"]
    jpy_countries = ["Japan", "日本", "Tokyo", "東京"]

    pair_keywords = {
        "EUR/USD": ["EUR/USD", "ユーロドル", "Euro Dollar"],
        "USD/JPY": ["USD/JPY", "ドル円", "Dollar Yen"],
        "EUR/JPY": ["EUR/JPY", "ユーロ円", "Euro Yen"]
    }

    @staticmethod
    def is_currency_related(article: Dict) -> bool:
        source = article.get("source", "")
        headline = article.get("headline", "")
        summary = article.get("summary", "")
        url = article.get("url", "")
        text = (headline + " " + summary + " " + url).lower()
        # ソース判定
        for s in FinnhubNewsCollector.usd_sources + FinnhubNewsCollector.eur_sources + FinnhubNewsCollector.jpy_sources:
            if s.lower() in source.lower():
                return True
        # 国名判定
        for c in FinnhubNewsCollector.usd_countries + FinnhubNewsCollector.eur_countries + FinnhubNewsCollector.jpy_countries:
            if c.lower() in text:
                return True
        # 内容判定（headline, summary, urlに通貨関連ワードが含まれる場合）
        for k in FinnhubNewsCollector.currency_keywords:
            if k.lower() in text:
                return True
        return False

    @staticmethod
    def classify_currency_pair(article: Dict) -> str:
        text = (article.get("headline", "") + " " + article.get("summary", "") + " " + article.get("url", "")).lower()
        for pair, keywords in FinnhubNewsCollector.pair_keywords.items():
            for kw in keywords:
                if kw.lower() in text:
                    return pair
        return "OTHER"
    
    @staticmethod
    def classify_currency_pair_from_text(headline: str, summary: str, url: str) -> str:
        """
        headline, summary, urlから通貨ペアを判定
        """
        text = (headline or "") + " " + (summary or "") + " " + (url or "")
        text = text.lower()
        pair_keywords = {
            "EUR/USD": ["eur/usd", "ユーロドル", "euro dollar"],
            "USD/JPY": ["usd/jpy", "ドル円", "dollar yen"],
            "EUR/JPY": ["eur/jpy", "ユーロ円", "euro yen"]
        }
        for pair, keywords in pair_keywords.items():
            for kw in keywords:
                if kw in text:
                    return pair
        return "OTHER"

    def get_forex_news(self, limit: int = 50, minutes_back: int = 30) -> List[Dict]:
        """
        為替関連ニュースを取得（時間範囲指定対応）
        
        Args:
            limit: 取得するニュース数の上限
            minutes_back: 何分前までのニュースを取得するか
            
        Returns:
            為替ニュース記事のリスト
        """
        all_news = []
        
        for category in self.forex_categories:
            news = self.get_market_news(category, limit // len(self.forex_categories), minutes_back)
            all_news.extend(news)
        
        # 重複除去（URLベース）
        seen_urls = set()
        unique_news = []
        for article in all_news:
            if article.get("url") and article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                # キーワード判定を元に戻す
                if self.is_currency_related(article):
                    unique_news.append(article)
        
        # 日付でソート（新しい順）
        unique_news.sort(key=lambda x: x.get("datetime", 0), reverse=True)
        
        return unique_news[:limit]
    
    def convert_to_news_article(self, finnhub_article: Dict) -> Optional[NewsArticle]:
        """
        Finnhub APIのレスポンスをNewsArticleモデルに変換
        
        Args:
            finnhub_article: Finnhub APIから取得した記事データ
            
        Returns:
            NewsArticleオブジェクト、または変換失敗時はNone
        """
        try:
            # 必須フィールドの確認
            if not finnhub_article.get("headline") or not finnhub_article.get("url"):
                d.print(f"Missing required fields in article: {finnhub_article}", level="warning")
                return None
            
            # datetimeの変換（Unix timestampから）
            datetime_unix = finnhub_article.get("datetime", 0)
            if datetime_unix:
                published = datetime.fromtimestamp(datetime_unix)
            else:
                published = datetime.now()
            
            # 要約の生成
            summary_text = finnhub_article.get("summary", "")
            if summary_text and len(summary_text) > 100:
                # 長い場合は要約を生成
                summary = summarize_text(summary_text)
            else:
                # 短い場合はそのまま使用、なければheadlineを使用
                summary = summary_text or finnhub_article.get("headline", "")
            
            currency_pair = self.classify_currency_pair(finnhub_article)
            full_text = finnhub_article.get("summary", "") + " " + finnhub_article.get("headline", "")
            currency_tags = detect_currency_tags(full_text)

            return NewsArticle(
                category="finnhub_forex",
                title=finnhub_article["headline"],
                summary=summary,
                url=finnhub_article["url"],
                published=published,
                currency_tags=currency_tags
            )
            
        except Exception as e:
            d.print(f"Error converting Finnhub article to NewsArticle: {e}", level="error")
            return None
    
    def fetch_and_store_finnhub_news(self, limit: int = 30, minutes_back: int = 30) -> int:
        """
        Finnhub APIからニュースを取得してデータベースに保存（時間範囲指定対応・バッチ処理版）
        
        Args:
            limit: 取得するニュース数の上限
            minutes_back: 何分前までのニュースを取得するか
            
        Returns:
            新規保存されたニュース記事数
        """
        session = SessionLocal()
        new_articles_count = 0
        batch_size = 5  # Finnhubは処理が重いので小さめのバッチサイズ
        current_batch = 0
        
        try:
            d.print(f"Starting Finnhub news collection (limit: {limit}, last {minutes_back} minutes)", level="info")
            
            # Finnhubからニュースを取得（時間範囲指定）
            finnhub_news = self.get_forex_news(limit, minutes_back)
            
            if not finnhub_news:
                d.print(f"No news retrieved from Finnhub API for the last {minutes_back} minutes", level="warning")
                return 0
            
            d.print(f"Processing {len(finnhub_news)} articles from Finnhub (last {minutes_back} minutes)", level="info")
            
            for article_data in finnhub_news:
                try:
                    # キーワード判定を元に戻す
                    if not self.is_currency_related(article_data):
                        continue
                    existing = session.query(NewsArticle).filter_by(
                        url=article_data.get("url")
                    ).first()
                    if existing:
                        d.print(f"⏩ Article already exists: {article_data.get('headline', 'No title')[:50]}...", level="debug")
                        continue
                    news_article = self.convert_to_news_article(article_data)
                    if news_article:
                        session.add(news_article)
                        new_articles_count += 1
                        current_batch += 1
                        d.print(f"✅ New Finnhub article: {news_article.title[:50]}...", level="info")
                        
                        # バッチサイズに達したら中間コミット
                        if current_batch >= batch_size:
                            try:
                                session.commit()
                                d.print(f"📦 Finnhub batch commit: {current_batch} articles saved", level="info")
                                current_batch = 0
                            except Exception as commit_error:
                                d.print(f"❌ Finnhub batch commit failed: {commit_error}", level="error")
                                session.rollback()
                                current_batch = 0
                    else:
                        d.print(f"❌ Failed to convert article: {article_data.get('headline', 'No title')[:50]}...", level="warning")
                        
                except Exception as article_error:
                    d.print(f"Error processing Finnhub article: {article_error}", level="error")
                    continue
            
            # 残りの記事をコミット
            if current_batch > 0:
                try:
                    session.commit()
                    d.print(f"📦 Finnhub final batch commit: {current_batch} articles saved", level="info")
                except Exception as commit_error:
                    d.print(f"❌ Finnhub final batch commit failed: {commit_error}", level="error")
                    session.rollback()

            d.print(f"🆗 Finnhub news collection completed. New articles: {new_articles_count}", level="info")
            
            return new_articles_count
            
        except Exception as e:
            session.rollback()
            d.print(f"Error in fetch_and_store_finnhub_news: {e}", level="error")
            return 0
        finally:
            session.close()


def fetch_finnhub_forex_news(limit: int = 30, minutes_back: int = 30) -> int:
    """
    Finnhub APIから為替ニュースを取得してDBに保存する関数（時間範囲指定対応）
    （既存のニュース収集システムと統合しやすいよう独立した関数として提供）
    
    Args:
        limit: 取得するニュース数の上限
        minutes_back: 何分前までのニュースを取得するか
        
    Returns:
        新規保存されたニュース記事数
    """
    try:
        collector = FinnhubNewsCollector()
        return collector.fetch_and_store_finnhub_news(limit, minutes_back)
    except Exception as e:
        d.print(f"Error in fetch_finnhub_forex_news: {e}", level="error")
        return 0


if __name__ == "__main__":
    # テスト実行（過去30分間のニュース）
    d.print("Testing Finnhub News Collector (last 30 minutes)...", level="info")
    result = fetch_finnhub_forex_news(limit=10, minutes_back=30)
    d.print(f"Test completed. New articles: {result}", level="info")
