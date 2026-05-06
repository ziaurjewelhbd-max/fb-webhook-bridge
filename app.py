import requests
from flask import Flask, request

app = Flask(__name__)

# আপনার টোকেনগুলো এখানে সেট করা হয়েছে
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRbgQY6y9Wb42bT7lBu9H9ROpe5WyH4wll6U4rkOXdcJIT19ghp3KU6RnvptZBfbGOHCEZC31jmuZBiozJw42kLqXxJXmuhkFSY0BuZC5ZCZCUSOUAiOUQyC7py2zGimv1L1VaCfyW7GYJFlMSn2MusVyKYnQRrhgsgUBdC6asM5fk9cFT2YssqkgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

def send_message(recipient_id, text):
    """ইউজারকে মেসেজ পাঠানোর ফাংশন"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

@app.route('/', methods=['GET'])
def verify():
    # ফেসবুক ভেরিফিকেশন (যা আপনি ইতিপুর্বেই সফলভাবে করেছেন)
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == MY_VERIFY_TOKEN:
        return challenge, 200
    return "Verification Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                
                # যদি কেউ টেক্সট মেসেজ পাঠায়
                if messaging_event.get("message"):
                    message_text = messaging_event["message"].get("text")
                    
                    if message_text:
                        print(f"Received message: {message_text}")
                        # ইউজারকে একটি অটো-রিপ্লাই দেওয়া
                        send_message(sender_id, f"আপনি লিখেছেন: {message_text}. আমি এখন পিডিএফ-এর জন্য অপেক্ষা করছি!")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
