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

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            # 古いコードの仕様（リスト形式）だった場合の互換性ケア
            if isinstance(data, list):
                return {}
            return data
        except:
            return {}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

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
    old_history = load_history()  # 辞書形式で取得 {"商品コード_店舗ID": {"product_name": "...", "shop_title": "..."}}
    
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
                    # 現在の在庫情報を記憶
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
        for old_id, info in old_history.items():
            if old_id not in current_history:
                sold_out_items.append(f"❌ 【{info['product_name']}】\n・{info['shop_title']}\n ※売り切れました")

    # 3. 新入荷の判定（今回あるのに、前回なかったもの）
    all_new_items = []
    for unique_id, info in current_history.items():
        if unique_id not in old_history:
            shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={info['shop_code']}"
            item_msg = f"🔔 【{info['product_name']}】\n・{info['shop_title']}\n  住所: {info['shop_address']}\n  URL: {shop_url}"
            all_new_items.append(item_msg)

    # 4. メッセージの構築と送信
    messages_to_send = []
    
    if len(all_new_items) > 0:
        messages_to_send.append("🌟 【入荷検知】\n\n" + "\n\n".join(all_new_items))
        
    if len(sold_out_items) > 0:
        messages_to_send.append("⚠️ 【完売・在庫切れ】\n\n" + "\n\n".join(sold_out_items))

    if len(messages_to_send) > 0:
        final_msg = "\n\n============\n\n".join(messages_to_send)
        send_line_message(final_msg)
        save_history(current_history)  # 最新の在庫状況（名前付き）で上書き保存
        print(f"通知を送信しました。（入荷: {len(all_new_items)}件 / 完売: {len(sold_out_items)}件）")
    else:
        # 通知がなくても、在庫が減ってデータに変化があった場合は保存ファイルを更新
        if old_history.keys() != current_history.keys():
            save_history(current_history)
        print("変化はありませんでした。")

# main.py の最下部をこのように修正

if __name__ == "__main__":
    import os
    # GitHub Actionsの環境変数からモードを取得
    mode = os.environ.get("RUN_MODE", "check")

    if mode == "summary":
        print("【サマリーモード】現在の全在庫を出力します...")
        current_history = load_history()
        
        if not current_history:
            send_line_message("現在、在庫がある店舗はありません。")
        else:
            # 商品ごとにデータを整理
            summary_data = {}
            for unique_id, info in current_history.items():
                p_name = info["product_name"]
                if p_name not in summary_data:
                    summary_data[p_name] = []
                shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={info['shop_code']}"
                summary_data[p_name].append(f"・{info['shop_title']}\n  {shop_url}")

            # メッセージ構築
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
        # 通常の定期実行（変化チェック）
        check_stock()
