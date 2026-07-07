import requests
import json
import os

# --- 設定項目 ---
TARGET_PRODUCTS = [
    {"name": "めじるしアクセサリー ～ヨッシーコレクション～", "code": "4582769916830"},
    {"name": "サンリオ けろけろパーティー めじるしアクセサリー", "code": "4570118186782"},
    {"name": "サンリオ～なりきりメンダコ～ ", "code": "4582769746017"},
    {"name": "サンリオ カラともマスコット", "code": "4570118205568"},
    {"name": "サンリオ 手作りおやつチャーム", "code": "4582769978906"},
    {"name": "サンリオ キーリングハンガー", "code": "4582769978890"},
    {"name": "サンリオキャラクターズ ななほしカラフルマルチチャーム", "code": "4582769978944"}
]

# LINE設定
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.environ.get("LINE_USER_ID")

API_URL = "https://gashapon.jp/shop/leaflet/getShopProducts.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/126.0.0.0",
    "Referer": "https://gashapon.jp/products/detail.php?jan_code=4570118186782000"
}
HISTORY_FILE = "notified_shops.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

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
    
    # 1. 現在在庫がある店舗IDを全商品分集める
    current_all_ids = []
    product_results = {} # 商品ごとのデータ保持用
    shop_info_map = {}   # 店舗情報をIDから逆引きするための辞書

    for product in TARGET_PRODUCTS:
        payload = {"product_code": product["code"], "center_lat": "35.6812", "center_lng": "139.7671", "gplus_type": "gplus", "map_distance_flg": "false"}
        try:
            response = requests.post(API_URL, data=payload, headers=HEADERS)
            data = response.json()
            shops = data.get("gplus_data", [])
            product_results[product["code"]] = shops
            for shop in shops:
                if shop.get("shop_pref_code") in ["13", "12"]:
                    unique_id = f"{product['code']}_{shop['id']}"
                    current_all_ids.append(unique_id)
                    # 売り切れ通知用に店舗名と商品名を保存しておく
                    shop_info_map[unique_id] = {
                        "product_name": product["name"],
                        "shop_title": shop["shop_title"]
                    }
        except Exception as e:
            print(f"データ取得エラー ({product['name']}): {e}")

    # 2. 【変更点】在庫切れ（＝前回あったのに今回消えた）店舗を抽出
    # ※ただし、初回実行時（historyファイルが空）に大量の売り切れ通知が出ないよう、historyがある場合のみ判定
    sold_out_items = []
    if len(notified_list) > 0:
        for old_id in notified_list:
            if old_id not in current_all_ids:
                # 過去の履歴（ファイル等）から前回の名前を復元するか、現在のリストにない場合は簡易表記
                info = shop_info_map.get(old_id, {"product_name": "対象商品", "shop_title": f"店舗(ID:{old_id.split('_')[-1]})"})
                sold_out_items.append(f"❌ 【{info['product_name']}】\n・{info['shop_title']}\n ※売り切れました")

    # 3. 履歴のうち、現在も在庫があるものだけを残す
    new_history = [uid for uid in notified_list if uid in current_all_ids]
    
    # 4. 未通知の在庫店舗を探す（新入荷）
    all_new_items = []
    for product in TARGET_PRODUCTS:
        shops = product_results.get(product["code"], [])
        for shop in shops:
            if shop.get("shop_pref_code") not in ["13", "12"]:
                continue
            
            unique_id = f"{product['code']}_{shop['id']}"
            if unique_id not in new_history:
                shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={shop['shop_code']}"
                item_msg = f"🔔 【{product['name']}】\n・{shop['shop_title']}\n  住所: {shop['shop_address']}\n  URL: {shop_url}"
                all_new_items.append(item_msg)
                new_history.append(unique_id)

    # 5. 【変更点】新入荷と売り切れ、それぞれのメッセージを構築して送信
    messages_to_send = []
    
    if len(all_new_items) > 0:
        messages_to_send.append("🌟 【入荷検知】\n\n" + "\n\n".join(all_new_items))
        
    if len(sold_out_items) > 0:
        messages_to_send.append("⚠️ 【完売・在庫切れ】\n\n" + "\n\n".join(sold_out_items))

    if len(messages_to_send) > 0:
        # 入荷と売り切れを1つのメッセージにまとめて送信
        final_msg = "\n\n============\n\n".join(messages_to_send)
        send_line_message(final_msg)
        save_history(new_history)
        print(f"通知を送信しました。（入荷: {len(all_new_items)}件 / 完売: {len(sold_out_items)}件）")
    else:
        # メッセージの送信はなくても、在庫切れで履歴が減った場合は保存する
        if len(notified_list) != len(new_history):
            save_history(new_history)
        print("変化はありませんでした。")

if __name__ == "__main__":
    check_stock()
