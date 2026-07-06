import requests
import json
import os

# --- 設定項目 ---
# 商品名を固定で設定します
PRODUCT_NAME = "サンリオキャラクターズ 手作りおやつチャーム ＃アイシングクッキー＆パッケージ"
# DiscordのWebhook URLをここに貼り付けてください
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

API_URL = "https://gashapon.jp/shop/leaflet/getShopProducts.php"
PAYLOAD = {
    "product_code": "4582769978906",
    "center_lat": "35.6812",
    "center_lng": "139.7671",
    "gplus_type": "gplus",
    "map_distance_flg": "false"
}
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

def check_stock():
    print("在庫をチェック中...")
    try:
        response = requests.post(API_URL, data=PAYLOAD, headers=HEADERS)
        data = response.json()
        shops = data.get("gplus_data", [])
        
        # 今回の検索でヒットした、東京(13)・千葉(12)の店舗リスト
        current_stock_ids = [s['id'] for s in shops if s.get("shop_pref_code") in ["13", "12"]]
        
        # 履歴を読み込み
        notified_list = load_history()
        
        # 【重要】今回リストにいない店舗は履歴から削除（在庫切れ＝通知済みを解除）
        new_history = [shop_id for shop_id in notified_list if shop_id in current_stock_ids]
        
        found_new = False
        # 全店舗をチェック
        for shop in shops:
            if shop.get("shop_pref_code") not in ["13", "12"]:
                continue
            
            shop_id = shop['id']
            # 通知済みリストにIDがなければ通知
            if shop_id not in new_history:
                # 商品名を取得（APIから取得したデータ内の product_name を参照）
                product_name = data.get("product_name", "不明な商品")
                # URLを修正（shop_codeを使用）
                shop_url = f"https://gashapon.jp/shop/shop.php?shop_code={shop['shop_code']}"
                msg = f"🔔 【入荷検知】\n商品: {product_name}\n店舗: {shop['shop_title']}\n住所: {shop['shop_address']}\n詳細URL: {shop_url}"
                res = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                if res.status_code in [200, 204]:
                    new_history.append(shop_id)
                    found_new = True
                    print(f"通知送信: {shop['shop_title']}")
        
        # 履歴を更新（削除・追加を反映）
        save_history(new_history)
        if not found_new:
            print("新しい在庫変動は見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    check_stock()
