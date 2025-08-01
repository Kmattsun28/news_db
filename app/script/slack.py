import os
import requests
import time
import json

# news posting incomming webhook
NEWS_WEBHOOK_URL = os.getenv("NEWS_WEBHOOK_URL")

def post_news_to_slack(news_content):
    """
    Slackにニュースを投稿する関数
    :param news_content: ニュースの内容
    """
    payload = {
        "text": f"```{news_content}```",
        "username": "News Bot",
        "icon_emoji": ":newspaper:"
    }
    
    try:
        response = requests.post(NEWS_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("ニュースをSlackに投稿しました")
    except requests.RequestException as e:
        print(f"Slackへのニュース投稿に失敗しました: {e}")

# 環境変数から設定を取得
BASE_URL = os.getenv("BASE_URL")
PAIRS = os.getenv("FOREX_PAIRS", "USDJPY").split(",")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", 60))

def fetch_signal_and_notify():
    for pair in PAIRS:
        try:
            # AIシグナルを取得
            endpoint_url = f"{BASE_URL}/api/qwen_signal/{pair}?days=10"
            response = requests.get(endpoint_url)
            response.raise_for_status()
            data = response.json()
            
            # 結果をパース（"買い 0.85"のような文字列から）
            content = data.get("content", "").strip()
            signal_type = "不明"
            confidence = 0.0
            
            if "買い" in content:
                signal_type = "買い :chart_with_upwards_trend:"
                confidence = float(content.split(" ")[1]) if len(content.split(" ")) > 1 else 0.0
            elif "売り" in content:
                signal_type = "売り :chart_with_downwards_trend:"
                confidence = float(content.split(" ")[1]) if len(content.split(" ")) > 1 else 0.0
            
            # Slack用メッセージ作成
            message = f"""
*AIシグナルアラート: {pair}*
判断: *{signal_type}*
信頼度: *{confidence:.2f}*
"""
            
            # 判断の根拠（thinkingから抜粋）
            thinking = data.get("thinking_content", "")
            if thinking:
                # 長すぎる場合は省略（Slackの制限）
                if len(thinking) > 1000:
                    thinking = thinking[:997] + "..."
                message += f"\n*判断根拠:*\n```{thinking}```"
            
            # Slackに送信
            payload = {"text": message}
            slack_response = requests.post(SLACK_WEBHOOK_URL, json=payload)
            slack_response.raise_for_status()
            print(f"[{pair}] シグナル通知送信完了")
            
        except Exception as e:
            error_message = f"エラー発生: {pair}シグナル取得・通知に失敗 - {str(e)}"
            print(error_message)
            # エラーもSlackに通知
            payload = {"text": f":warning: {error_message}"}
            try:
                requests.post(SLACK_WEBHOOK_URL, json=payload)
            except:
                pass

