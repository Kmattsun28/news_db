import time
import unicodedata
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from app.script.debug import debug_printer

def extract_article_text(url: str) -> str:
    driver = None
    try:
        # debug_printer.print(f"Seleniumスクレイピング開始: {url}", "debug")
        
        # Chromeの設定
        options = Options()
        options.add_argument('--headless')  # ヘッドレスモード
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        # 追加の安定化オプション
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # 画像読み込みを無効化して高速化
        
        # ChromeとChromeDriverのメジャーバージョンを指定（ここでは120）
        options.set_capability('browserVersion', '120')
        
        # 自動的に適切なChromedriverをインストール
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)  # タイムアウトを30秒から15秒に短縮
        # driver.implicitly_wait(5)  # 要素待機時間を短縮
        
        # URLにアクセス
        driver.get(url)
        
        # JavaScript実行とページ読み込み完了を待つ（短縮）
        time.sleep(5)  # 5秒から2秒に短縮
        
        # 最終的なURL（リダイレクト後）
        final_url = driver.current_url
        debug_printer.print(f"最終URL: {final_url}", "debug")
        
        # ページのHTMLソースを取得
        page_source = driver.page_source
        
        # HTML構造をファイルに保存（デバッグ用）
        # with open("./data/article.txt", "w", encoding="utf-8") as f:
        #     f.write(f"URL: {final_url}\n\n")
        #     f.write(page_source[:5000])  # 最初の5000文字
            
        # BeautifulSoupでHTML解析
        soup = BeautifulSoup(page_source, "html.parser")
        
        # セレクタ候補一覧
        candidates = [
            "article", "div.article", "div.article-body", "main", "div#main-content",
            "div.content", "div.post-content", "div.entry-content", "div#content",
            "div.story-body", ".news-article", ".story", "#story-body", ".post-body",
            "#article-body", ".article-content", ".story-content", ".news-content",
            ".article__body", ".article__content", ".story__body"
        ]
        
        # セレクタで本文検索
        for selector in candidates:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        text = element.text.strip()
                        if len(text) > 50:
                            debug_printer.print(f"セレクタ {selector} で本文を取得: {len(text)} 文字")
                            return text
            except Exception as e:
                continue
        
        # 段落から本文抽出
        paragraphs = driver.find_elements(By.TAG_NAME, "p")
        debug_printer.print(f"段落数: {len(paragraphs)}")
        
        meaningful_ps = [p.text for p in paragraphs if len(p.text.strip()) > 20]
        body = "\n".join(meaningful_ps).strip()
        
        if len(body) > 50:
            debug_printer.print(f"段落から本文を取得: {len(body)} 文字")
            return body
        else:
            debug_printer.print("十分な長さの本文を見つけられませんでした", "warning")
            return ""
            
    except Exception as e:
        debug_printer.print(f"スクレイピングエラー - {url}: {str(e)}", "error")
        return ""
    finally:
        # ブラウザを確実に終了
        if driver:
            try:
                driver.quit()
            except:
                pass

def detect_currency_tags(text: str) -> list:
    """
    Detect related currency tags (USD, EUR, JPY) from news text using extensive keyword lists.
    Handles Japanese summaries and full-width/half-width variations.
    """
    # Normalize text to NFKC to convert full-width to half-width, then lowercase
    normalized = unicodedata.normalize('NFKC', text)
    lower = normalized.lower()
    
    # --- 修正：重要な経済指標や金融用語を追加 ---
    keywords = {
        "USD": [
            # Basic USD terms
            "usd", "us dollar", "dollar", "dollars", "greenback", "米ドル", "ドル", "米国ドル",
            # Central bank and policy
            "federal reserve", "fed", "frb", "米連邦準備制度理事会", "米連銀", "フェデラルリザーブ",
            "fomc", "FOMC", "米金融政策", "米利上げ", "米利下げ", "金利決定", "政策金利", "Trump", "president", "米大統領", "トランプ大統領", "トランプ",
            "jerome powell", "パウエル", "frb議長", "federal funds rate",
            "federal open market committee", "連邦公開市場委員会", 
            # Economic indicators
            "gdp", "米国gdp", "米gdp", "アメリカgdp", "国内総生産",
            "cpi", "米国cpi", "米cpi", "消費者物価指数", "インフレ", "物価上昇",
            "pce", "personal consumption expenditures", "個人消費支出",
            "ppi", "米国ppi", "米ppi", "生産者物価指数",
            "employment", "unemployment", "米国雇用統計", "米雇用統計", "失業率", "雇用者数",
            "nonfarm payrolls", "nfp", "非農業部門雇用者数", "雇用統計",
            "retail sales", "米国小売売上高", "米小売売上高", "小売売上",
            "durable goods orders", "耐久財受注",
            "ism manufacturing", "ism non-manufacturing", "ism製造業景況指数", "ism非製造業景況指数",
            "housing market", "住宅市場", "住宅着工件数", "住宅販売",
            "consumer confidence", "消費者信頼感指数", "消費者心理",
            "trade balance", "trade deficit", "貿易収支", "貿易赤字",
            "public debt", "sovereign debt", "財政赤字", "政府債務",
            "treasury", "米国債", "米債", "国債利回り", "10年債",
            "yield", "利回り", "債券利回り","米国株",
            # Countries and regions
            "united states", "america", "usa", "米国", "アメリカ", "米",
            "washington", "ワシントン", "ny", "ニューヨーク",
            # Currency pairs
            "usd/jpy", "usdjpy", "ドル円", "ドル/円", "dollar yen",
            "eur/usd", "eurusd", "ユーロドル", "ユーロ/ドル", "euro dollar",
            # General FX terms
            "fx", "foreign exchange", "為替", "為替相場", "金融政策", "geopolitical risk", "地政学リスク",
            # News sources
            "cnbc", "bloomberg", "reuters", "wsj", "wall street journal", "marketwatch", "forexlive", 
            "yahoo finance", "business insider", "forbes", "ny times", "ap", "fox business", "cnn", 
            "barron's", "motley fool", "seeking alpha", "us treasury", "usa today", "thestreet", 
            "investopedia", "kiplinger", "morningstar", "s&p global", "nasdaq", "zacks", "the economist", 
            "politico", "fortune", "us news", "abc news", "cbs news", "nbc news", "npr"
        ],
        "EUR": [
            # Basic EUR terms
            "eur", "euro", "euros", "ユーロ", "欧州通貨", "欧州共通通貨",
            # Central bank and policy
            "european central bank", "ecb", "欧州中央銀行", "欧州中銀", "ヨーロッパ中央銀行",
            "christine lagarde", "ラガルド", "ecb政策決定", "欧州金融政策",
            "欧州利上げ", "欧州利下げ", "ユーロ圏金利", "ecb interest rate decision", "deposit facility rate",
            # Economic indicators
            "eurozone gdp", "ユーロ圏gdp", "欧州gdp", "欧州経済成長",
            "eurozone cpi", "ユーロ圏cpi", "欧州cpi", "欧州インフレ", "欧州物価",
            "eurozone ppi", "ユーロ圏ppi", "欧州ppi",
            "eurozone pmi", "ユーロ圏pmi", "欧州pmi", "製造業pmi", "サービス業pmi",
            "zew economic sentiment", "zew景況感指数",
            "eurozone unemployment", "ユーロ圏失業率", "欧州失業率",
            "eurozone retail sales", "ユーロ圏小売売上高", "欧州小売売上",
            "german gdp", "ドイツgdp", "独gdp", "ドイツ経済",
            "french gdp", "フランスgdp", "仏gdp", "フランス経済",
            "public debt", "sovereign debt", "財政赤字", "政府債務",
            # Countries and regions
            "eurozone", "ユーロ圏", "ユーロ域", "欧州", "ヨーロッパ",
            "germany", "ドイツ", "独", "berlin", "ベルリン","ドイツ株",
            "france", "フランス", "仏", "paris", "パリ","フランス株",
            "italy", "イタリア", "伊", "spain", "スペイン", "西",
            "netherlands", "オランダ", "蘭", "belgium", "ベルギー",
            # Currency pairs
            "eur/usd", "eurusd", "ユーロドル", "ユーロ/ドル", "euro dollar",
            "eur/jpy", "eurjpy", "ユーロ円", "ユーロ/円", "euro yen",
            # General FX terms
            "fx", "foreign exchange", "為替", "為替相場", "金融政策", "geopolitical risk", "地政学リスク",
            # News sources
            "financial times", "handelsblatt", "le monde", "bbc", "the guardian", "dw", "el país", 
            "il sole 24 ore", "les echos", "frankfurter allgemeine", "euronews", "swissinfo", "rte", 
            "süddeutsche zeitung", "la stampa", "la repubblica", "die welt", "le figaro", "der spiegel", 
            "politico europe", "de tijd", "nrc handelsblad", "het financieele dagblad", "børsen", 
            "dagens nyheter", "svenska dagbladet", "aftenposten", "helsingin sanomat", "público", 
            "expresso", "kathimerini", "cyprus mail", "irish times", "irish independent", "the times", 
            "the telegraph", "sky news", "l'express", "ouest-france", "trouw", "volkskrant", "vrt nws", 
            "nos", "rtl nieuws", "le soir", "la libre belgique"
        ],
        "JPY": [
            # Basic JPY terms
            "jpy", "japanese yen", "yen", "日本円", "円", "円相場", "円安", "円高",
            # Central bank and policy
            "bank of japan", "boj", "日本銀行", "日銀", "ボージェイ",
            "黒田東彦", "植田和男", "日銀総裁", "金融政策決定会合", "政策決定会合", "boj interest rate decision",
            "日本金融政策", "日銀政策", "利上げ", "利下げ", "金融緩和", "量的緩和", "為替介入", "介入",
            "マイナス金利", "イールドカーブコントロール", "ycc",
            # Economic indicators
            "japan gdp", "日本gdp", "日gdp", "日本経済成長",
            "japan cpi", "日本cpi", "日cpi", "消費者物価指数", "コア指数",
            "japan ppi", "日本ppi", "日ppi", "企業物価指数",
            "japan pmi", "日本pmi", "日pmi", "製造業pmi", "サービス業pmi",
            "japan unemployment", "日本失業率", "日失業率", "完全失業率",
            "japan retail sales", "日本小売売上高", "日小売売上", "小売業販売額",
            "trade balance", "balance of payments", "貿易収支", "国際収支", "貿易黒字", "貿易赤字",
            "current account", "経常収支", "経常黒字", "経常赤字",
            "tankan", "短観", "日銀短観", "企業短期経済観測調査", "tankan survey",
            "machinery orders", "機械受注", "設備投資",
            "industrial production", "鉱工業生産指数", "生産指数",
            "foreign exchange reserves", "外貨準備高",
            # Countries and regions
            "japan", "日本", "nippon", "nihon", "jp",
            "tokyo", "東京", "osaka", "大阪", "yokohama", "横浜",
            # Currency pairs
            "usd/jpy", "usdjpy", "ドル円", "ドル/円", "dollar yen",
            "eur/jpy", "eurjpy", "ユーロ円", "ユーロ/円", "euro yen",
            # General FX terms
            "fx", "foreign exchange", "為替", "為替相場", "金融政策", "geopolitical risk", "地政学リスク",
            # News sources
            "nikkei", "日経", "nhk", "bloomberg japan", "reuters japan", "日本経済新聞", "東洋経済", "yahoo!ニュース",
            "朝日新聞", "読売新聞", "毎日新聞", "産経新聞", "共同通信", "時事通信"
        ]
    }
    
    tags = []
    for code, kws in keywords.items():
        for kw in kws:
            if kw in lower:
                tags.append(code)
                break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags