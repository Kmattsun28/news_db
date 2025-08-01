import websocket
import time
import json
import os

from app.script.slack import post_news_to_slack
from app.script.summarizer import summarize_news

WS_API_ENDPOINT = 'wss://api.synoptic.com/v1/ws'
API_KEY = os.getenv('WS_API_KEY')
RECONNECT_DELAY_SEC = 1

def run_ws():
    ws_url = f"{WS_API_ENDPOINT}/on-stream-post?apiKey={API_KEY}"

    while True:
        try:
            ws = websocket.create_connection(ws_url)
            print('Connected to the server')
            while True:
                try:
                    message = ws.recv()
                    if message is None:
                        print('WebSocket connection closed by server')
                        break
                    print('Received message:', message)
                    try:
                        # jsonパース
                        msg_obj = json.loads(message)

                        if msg_obj.get("event") in ["ack", "sub_ack", "keep-alive"]:  # システムメッセージを除外
                            continue

                        elif msg_obj.get("data"):  
                            data_str = json.dumps(msg_obj["data"], ensure_ascii=False, indent=2)
                            print('data ->')
                            print(data_str)
                            # Slackに投稿（生データ）
                            post_news_to_slack(data_str)
                            
                            # ニュース記事の要約・投稿
                            summary = summarize_news(data_str)
                            print('Summary ->')
                            print(summary)
                            post_news_to_slack(summary)
                            
                    except Exception as e:
                        print('JSON decode error:', e)
                except websocket.WebSocketConnectionClosedException:
                    print('WebSocket connection closed')
                    break
                except Exception as e:
                    print('WebSocket error:', e)
                    break
        except Exception as e:
            print('WebSocket connection failed:', e)
        finally:
            try:
                ws.close()
            except Exception:
                pass
            print(f"Reconnecting in {RECONNECT_DELAY_SEC} seconds...")
            time.sleep(RECONNECT_DELAY_SEC)

if __name__ == "__main__":
    run_ws()