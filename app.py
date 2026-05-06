from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def verify():
    # ফেসবুক পোর্টালে আপনি যে টোকেন দেবেন সেটি এখানে লিখুন
    verify_token = "my_pdf_bot_token"
    
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return challenge, 200 # এখানে কোনো HTML ছাড়াই শুধু সংখ্যাটি যাবে
    return "Verification Failed", 403

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
