import requests
from flask import Flask, request
import PyPDF2
import io

app = Flask(__name__)

# আপনার টোকেন এবং ভেরিফাই টোকেন
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRX3JQ8arMkK0PURih9tSncgODgENBZCiJtlJpSKRSjBbIHPfXsLlPz2RTQjhO6wmxA5gX7ofaXT7l3z4HL7mIT8oPpoNaOwGfs1xFKZC1NTy7yw0wZCW3z7VhzHAAirCEnL0Ay6T13PHzMoKZA6WbTY7SZBw9qSZCM1yRQOG7Xyy71819SF7QVDgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

def send_message(recipient_id, text):
    """ফেসবুক পেজে মেসেজ পাঠানোর ফাংশন"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    response = requests.post(url, json=payload)
    print(f"Reply Status: {response.status_code}")

def extract_pdf_text(pdf_url):
    """পিডিএফ লিঙ্ক থেকে টেক্সট বের করার ফাংশন"""
    try:
        response = requests.get(pdf_url)
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            # প্রথম ২ পৃষ্ঠার টেক্সট পড়ার চেষ্টা করবে
            for page_num in range(min(len(reader.pages), 2)):
                page_text = reader.pages[page_num].extract_text()
                if page_text:
                    text += page_text
            return text[:1000] if text else "পিডিএফ-এ কোনো টেক্সট পাওয়া যায়নি (হয়তো এটি ইমেজ ফাইল)।"
    except Exception as e:
        return f"পিডিএফ পড়তে সমস্যা হয়েছে: {str(e)}"

@app.route('/', methods=['GET'])
def verify():
    """ফেসবুক ওয়েব হুক ভেরিফিকেশন"""
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == MY_VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    """মেসেজ রিসিভ করার মূল পয়েন্ট"""
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                
                # যদি ইউজার কোনো ফাইল (পিডিএফ) পাঠায়
                if "message" in messaging_event:
                    msg = messaging_event["message"]
                    
                    if "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment["type"] == "file":
                                pdf_url = attachment["payload"]["url"]
                                send_message(sender_id, "পিডিএফ পেয়েছি! আমি এটি পড়ার চেষ্টা করছি...")
                                
                                # টেক্সট এক্সট্রাক্ট করা
                                content = extract_pdf_text(pdf_url)
                                send_message(sender_id, f"পিডিএফ-এর সারসংক্ষেপ:\n{content}")
                    
                    # যদি শুধু টেক্সট পাঠায়
                    elif "text" in msg:
                        user_text = msg["text"]
                        print(f"Received Text: {user_text}")
                        send_message(sender_id, f"আপনি লিখেছেন: {user_text}. দয়া করে একটি পিডিএফ পাঠান যাতে আমি সেটি পড়ে দিতে পারি।")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    # Render সাধারণত পোর্ট ১০০০০ ব্যবহার করে
    app.run(host='0.0.0.0', port=10000)
