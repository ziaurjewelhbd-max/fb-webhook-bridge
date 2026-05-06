from flask import Flask, request

app = Flask(__name__)

# --- সেটিংস ---
# এই টোকেনটি আপনি ফেসবুক পোর্টালে 'Verify Token' বক্সে লিখবেন
MY_VERIFY_TOKEN = "my_pdf_bot_token"

@app.route('/', methods=['GET'])
def verify():
    """
    ফেসবুক এই এন্ডপয়েন্টে GET রিকোয়েস্ট পাঠিয়ে ভেরিফাই করে।
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # ভেরিফিকেশন লজিক
    if mode == "subscribe" and token == MY_VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return challenge, 200
    
    return "Verification Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    """
    ভেরিফাই হয়ে যাওয়ার পর ফেসবুক সব মেসেজ এই POST রিকোয়েস্টের মাধ্যমে পাঠাবে।
    """
    data = request.get_json()
    print("Received message:", data)
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    # Render-এর জন্য host এবং port সেট করা জরুরি
    app.run(host='0.0.0.0', port=5000)
