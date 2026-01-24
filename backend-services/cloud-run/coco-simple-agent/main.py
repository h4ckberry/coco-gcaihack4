import os
from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    # データを受け取る（ファイル名など）
    data = request.get_json()
    
    # ★★★ ここが重要：ログ出力 ★★★
    # Cloud Runでは print() するだけで Cloud Logging に出力されます
    print(f"🚀【起動確認】Cloud Run is ACTIVE!")
    print(f"📥 Received data: {data}")
    
    return "OK received", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
