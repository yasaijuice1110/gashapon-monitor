import requests
import json
import os

# --- 設定項目 ---
TARGET_PRODUCTS = [
    {"name": "めじるしアクセサリー ～ヨッシーコレクション～", "code": "4582769916830"},
    {"name": "サンリオ～なりきりメンダコ～ ", "code": "4582769746017"},
    {"name": "サンリオ カラともマスコット", "code": "4570118205568"},
    {"name": "サンリオキャラクターズ ななほしカラフルマルチチャーム", "code": "4582769978944"},
    {"name": "たまごっち めじるしアクセサリー", "code": "4582769979156"},
    {"name": "シュガーバニーズ ふわふわめじるしアクセサリー", "code": "4570118184573"}
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
TRACKED_PRODUCTS_FILE = "tracked_products.json"  # 追跡商品の管理用ファイル

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return {}
            return data
        except:
            return {}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def load_tracked_products():
    """前回実行時の追跡商品リストを読み込む"""
    if not os.path.exists(TRACKED_PRODUCTS_FILE):
        return {}
    with open(TRACKED_PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_tracked_products(tracked):
    """今回の追跡商品リストを保存する"""
    with open(TRACKED_PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracked, f, indent=4, ensure_ascii=False)

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

def get_target_product_changes():
    """TARGET_PRODUCTS の追加・削除を検知してメッセージ用の配列を返す（保存はここではしない）"""
    old_tracked = load_tracked_products()
    current_tracked = {p["code"]: p["name"] for p in TARGET_PRODUCTS}
    
    change_messages = []
    
    if not old_tracked:
        return change_messages
    
    # 新しく追加された商品を検知
    for code, name in current_tracked.items():
        if code not in old_tracked:
            change_messages.append(f"➕ 【対象商品に追加されました】\n・{name}")
            
    # リストから削除された商品を検知
    for code, name in old_tracked.items():
        if code not in current_tracked:
            change_messages.append(f"➖ 【対象商品から外されました】\n・{name}")
            
    return change_messages

def check_stock():
    print("全商品をチェック中...")
    old_history = load_history()
    
    # 1. 現在在庫がある店舗のデータを収集
    current_history = {}
    product_results = {}

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
                    current_history[unique_id] = {
                        "product_name": product["name"],
                        "shop_title": shop["shop_title"],
                        "shop_address": shop.get("shop_address", ""),
                        "shop_code": shop.get("shop_code", "")
                    }
        except Exception as e:
            print(f"データ取得エラー ({product['name']}): {e}")

    # 2. 売り切れの判定（前回あったのに、今回消えたもの）
    sold_out_items = []
    if len(old_history) > 0:
        target_codes = [p["code"] for p in TARGET_PRODUCTS]
        
        for old_id, info in old_history.items():
            if old_id not in current_history:
                product_code = old_id.split("_")[0]
                if product_code in target_codes:
                    sold_out_items.append(f"❌ 【{info['product_name']}】\n・{info['shop_title']}\n ※売り切れました")

    # 3. 新入荷の判定（今回あるのに、前回なかったもの）
    all_new_items = []
    for unique_id, info in current_history.items():
        if unique_id not in old_history:
            product_code = unique_id.split("_")[0]
            target_codes = [p["code"] for p in TARGET_PRODUCTS]
            if product_code in target_codes:
                shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={info['shop_code']}"
                item_msg = f"🔔 【{info['product_name']}】\n・{info['shop_title']}\n  住所: {info['shop_address']}\n  URL: {shop_url}"
                all_new_items.append(item_msg)

    # 4. メッセージの構築と送信
    messages_to_send = []
    
    # ✨ 入荷か完売が「1件以上」ある場合のみ、設定変更メッセージをチェックして合体させる
    if len(all_new_items) > 0 or len(sold_out_items) > 0:
        config_changes = get_target_product_changes()
        if len(config_changes) > 0:
            messages_to_send.append("⚙️ 【システム設定の変更】\n\n" + "\n\n".join(config_changes))
            # 通知に載せるので、ここで追跡管理ファイルを更新
            current_tracked = {p["code"]: p["name"] for p in TARGET_PRODUCTS}
            save_tracked_products(current_tracked)
    
    if len(all_new_items) > 0:
        messages_to_send.append("🌟 【入荷検知】\n\n" + "\n\n".join(all_new_items))
        
    if len(sold_out_items) > 0:
        messages_to_send.append("⚠️ 【完売・在庫切れ】\n\n" + "\n\n".join(sold_out_items))

    # 在庫のリアルな変化（入荷・完売）があった時だけLINEが飛ぶ
    if len(messages_to_send) > 0 and (len(all_new_items) > 0 or len(sold_out_items) > 0):
        final_msg = "\n\n============\n\n".join(messages_to_send)
        send_line_message(final_msg)
        save_history(current_history)
        print("在庫変化を検知したため、設定変更と合わせて通知を送信しました。")
    else:
        # 在庫変化がない時は、仮に商品の増減があってもLINEは送らず、ファイル同期も次回（在庫変化時）まで保留
        if old_history.keys() != current_history.keys():
            cleaned_history = {k: v for k, v in current_history.items()}
            save_history(cleaned_history)
        
        # 初回実行時のみ基準ファイルを作成
        if not os.path.exists(TRACKED_PRODUCTS_FILE):
            current_tracked = {p["code"]: p["name"] for p in TARGET_PRODUCTS}
            save_tracked_products(current_tracked)
            
        print("在庫に変化がないため、LINE通知はスキップしました。")

if __name__ == "__main__":
    import os
    mode = os.environ.get("RUN_MODE", "check")

    if mode == "summary":
        print("【サマリーモード】現在の全在庫を出力します...")
        current_history = load_history()
        
        if not current_history:
            send_line_message("現在、在庫がある店舗はありません。")
        else:
            summary_data = {}
            for unique_id, info in current_history.items():
                p_name = info["product_name"]
                if p_name not in summary_data:
                    summary_data[p_name] = []
                shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={info['shop_code']}"
                summary_data[p_name].append(f"=・{info['shop_title']}\n  {shop_url}")

            msg_lines = ["📋 【現在の在庫一覧サマリー】\n"]
            for p_name, shops in summary_data.items():
                msg_lines.append(f"📦 【{p_name}】")
                msg_lines.extend(shops)
                msg_lines.append("")

            final_msg = "\n".join(msg_lines).strip()
            if len(final_msg) > 4500:
                final_msg = final_msg[:4500] + "\n\n※文字数制限のため省略"
            
            send_line_message(final_msg)
            print("サマリーを送信しました。")
    else:
        check_stock()
