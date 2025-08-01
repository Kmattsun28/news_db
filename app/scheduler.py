from apscheduler.schedulers.background import BackgroundScheduler
from app.script.collect import collect_technical_data
from app.script.news_collect import fetch_and_store_rss, fetch_and_store_all_news
from app.script.slack import fetch_signal_and_notify
from datetime import datetime

# 定期実行のためのスケジューラを設定
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(collect_technical_data, 'interval', minutes=10, next_run_time=datetime.now())
    # RSS + Finnhub統合版のニュース収集を使用
    scheduler.add_job(fetch_and_store_all_news, 'interval', minutes=10, next_run_time=datetime.now())
    # scheduler.add_job(fetch_signal_and_notify, 'interval', minutes=60, next_run_time=datetime.now())
    scheduler.start()
