import requests
import json
import os

# --- 設定項目 ---
TARGET_PRODUCTS = [
    {"name": "サンリオキャラクターズ 手作りおやつチャーム", "code": "4582769978906"}
    {"name": "サンリオキャラクターズ アロハスイングコレクション", "code": "4582769829611"}
]

# LINE設定
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.environ.get("LINE_USER_ID")

API_URL = "https://gashapon.jp/shop/leaflet/getShopProducts.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://gashapon.jp/products/detail.php?jan_code=4570118186782000"
}
HISTORY_FILE = "notified_shops.json"

# 通知済みIDを読み込む関数
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

# 通知済みIDを保存する関数
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

# LINE通知送信関数
def send_line_message(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    return requests.post(url, headers=headers, json=payload)

def check_stock():
    print("全商品をチェック中...")
    notified_list = load_history()
    new_history = notified_list.copy()
    all_new_items = [] 

    for product in TARGET_PRODUCTS:
        payload = {"product_code": product["code"], "center_lat": "35.6812", "center_lng": "139.7671", "gplus_type": "gplus", "map_distance_flg": "false"}
        
        try:
            response = requests.post(API_URL, data=payload, headers=HEADERS)
            data = response.json()
            shops = data.get("gplus_data", [])
            
            for shop in shops:
                if shop.get("shop_pref_code") not in ["13", "12"]:
                    continue
                
                unique_id = f"{product['code']}_{shop['id']}"
                
                if unique_id not in notified_list:
                    shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={shop['shop_code']}"
                    item_msg = f"【{product['name']}】\n・{shop['shop_title']}\n  住所: {shop['shop_address']}\n  URL: {shop_url}"
                    all_new_items.append(item_msg)
                    new_history.append(unique_id)
        except Exception as e:
            print(f"エラー ({product['name']}): {e}")

    if len(all_new_items) > 0:
        msg = f"🔔 【入荷検知】\n\n" + "\n\n".join(all_new_items)
        send_line_message(msg)
        save_history(new_history)
    else:
        print("新しい入荷はありませんでした。")

if __name__ == "__main__":
    check_stock()
