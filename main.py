import requests
import os

# 環境変数から取得
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.environ.get("LINE_USER_ID")  # ここにグループIDが入る
PRODUCT_NAME = "サンリオキャラクターズ 手作りおやつチャーム ＃アイシングクッキー＆パッケージ"

def send_line_message(msg):
    # LINEに送るためのURL
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    # LINEへ送信
    requests.post(url, headers=headers, json=payload)

# 通知を送る箇所を以下のように書き換える
if shop_id not in new_history:
    shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={shop['shop_code']}"
    msg = f"🔔 【入荷検知】\n商品: {PRODUCT_NAME}\n店舗: {shop['shop_title']}\n住所: {shop['shop_address']}\n詳細: {shop_url}"
    
    send_line_message(msg)
    
    new_history.append(shop_id)
    found_new = True
