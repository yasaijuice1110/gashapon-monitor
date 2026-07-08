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
    {"name": "シュガーバニーズ ふわふわめじるしアクセサリー", "code": "4570118184573"},
    {"name": "HGドラゴンボール Another2", "code": "4582769889042"}
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
TRACKED_PRODUCTS_FILE = "tracked_products.json"  # ✨ 追跡商品の管理用ファイル

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
    """✨ 前回実行時の追跡商品リストを読み込む"""
    if not os.path.exists(TRACKED_PRODUCTS_FILE):
        return {}
    with open(TRACKED_PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_tracked_products(tracked):
    """✨ 今回の追跡商品リストを保存する"""
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

def check_target_product_changes():
    """✨ TARGET_PRODUCTS の追加・削除を検知してLINEに通知する"""
    old_tracked = load_tracked_products()  # {"code": "name"} の辞書
    current_tracked = {p["code"]: p["name"] for p in TARGET_PRODUCTS}
    
    config_messages = []
    
    # 新しく追加された商品を検知
    for code, name in current_tracked.items():
        if code not in old_tracked:
            config_messages.append(f"➕ 【対象商品に追加されました】\n・{name}\n(JAN: {code})")
            
    # リストから削除された商品を検知
    for code, name in old_tracked.items():
        if code not in current_tracked:
            config_messages.append(f"➖ 【対象商品から外されました】\n・{name}\n(JAN: {code})")
            
    if config_messages:
        # 変更があればLINEに通知し、管理ファイルを更新
        change_msg = "⚙️ 【システム設定の変更】\n\n" + "\n\n============\n\n".join(config_messages)
        send_line_message(change_msg)
        save_tracked_products(current_tracked)
        print("商品の追加/削除を検知して通知しました。")
    elif not old_tracked:
        # 初回実行時のみ、通知はせずファイルだけ作る
        save_tracked_products(current_tracked)

def check_stock():
    # ✨ まず商品の追加・削除がないかチェック
    check_target_product_changes()

    print("全商品をチェック中...")
    old_history = load_history()
    
    # 1. 現在在庫がある店舗のデータを収集
    current_history = {}
    product_results = {}

    for product in TARGET_PRODUCTS:
        payload = {"product_code": product["code"], "center_lat": "35.6812", "
