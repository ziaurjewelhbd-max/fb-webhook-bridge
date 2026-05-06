import requests
from flask import Flask, request
import PyPDF2
import io
import google.generativeai as genai
import sys

app = Flask(__name__)

# ১. আপনার ফেসবুক টোকেন
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRX3JQ8arMkK0PURih9tSncgODgENBZCiJtlJpSKRSjBbIHPfXsLlPz2RTQjhO6wmxA5gX7ofaXT7l3z4HL7mIT8oPpoNaOwGfs1xFKZC1NTy7yw0wZCW3z7VhzHAAirCEnL0Ay6T13PHzMoKZA6WbTY7SZBw9qSZCM1yRQOG7Xyy71819SF7QVDgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

# ২. আপনার দেওয়া Gemini API Key এখানে বসানো হয়েছে
GEMINI_API_KEY = "AIzaSyDkJZHIKx4k4glzI17PBr4zwzv2FckhYfc"
genai.configure(api_key=GEMINI_API_KEY)

# মডেল সেটআপ (Gemini 1.5 Flash ব্যবহার করা হচ্ছে)
model = genai.GenerativeModel('gemini-1.5-flash')

# ইউজার মেমোরি (যাতে পিডিএফ মনে রাখতে পারে)
user_sessions = {}

def log_message(message):
    """Render লগে আউটপুট দেখার জন্য"""
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

def send_message(recipient_id, text):
    """মেসেঞ্জারে উত্তর পাঠানোর ফাংশন"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    response = requests.post(url, json=payload)
    log_message(f"Message Status: {response.status_code}")

def extract_pdf_text(pdf_url):
    """পিডিএফ থেকে লেখা বের করার ফাংশন"""
    try:
        response = requests.get(pdf_url)
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text if text.strip() else None
    except Exception as e:
        log_message(f"PDF Extraction Error: {e}")
        return None

def get_gemini_response(pdf_content, user_query):
    """Gemini AI থেকে উত্তর নেওয়ার ফাংশন"""
    prompt = (
        f"Context from PDF:\n{pdf_content[:25000]}\n\n"
        f"User Question: {user_query}\n\n"
        f"Answer clearly in the language of the user's question."
    )
    try:
        # AI কে কল করা হচ্ছে
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log_message(f"Gemini API Error: {e}")
        return "দুঃখিত, Gemini AI এখন কাজ করছে না। হয়তো API Key-তে কোনো সীমাবদ্ধতা আছে।"

@app.route('/', methods=['GET'])
def verify():
    """ফেসবুক ভেরিফিকেশন"""
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == MY_VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    """মেসেজ রিসিভ করার পয়েন্ট"""
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                
                if "message" in messaging_event:
                    msg = messaging_event["message"]
                    
                    # যদি ইউজার ফাইল (PDF) পাঠায়
                    if "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment["type"] == "file":
                                pdf_url = attachment["payload"]["url"]
                                send_message(sender_id, "পিডিএফটি পেয়েছি। আমি এটি পড়ে নিচ্ছি...")
                                
                                pdf_text = extract_pdf_text(pdf_url)
                                if pdf_text:
                                    user_sessions[sender_id] = pdf_text
                                    send_message(sender_id, "পিডিএফ পড়া শেষ! এখন এই ফাইল সম্পর্কে আপনার যা জানার আছে আমাকে প্রশ্ন করুন।")
                                else:
                                    send_message(sender_id, "পিডিএফ থেকে কোনো টেক্সট পড়তে পারিনি। ফাইলটি কি স্ক্যান করা ছবি?")

                    # যদি ইউজার টেক্সট (প্রশ্ন) পাঠায়
                    elif "text" in msg:
                        query = msg["text"]
                        if sender_id in user_sessions:
                            # পিডিএফ মেমোরি থেকে উত্তর দিচ্ছে
                            answer = get_gemini_response(user_sessions[sender_id], query)
                            send_message(sender_id, answer)
                        else:
                            send_message(sender_id, "হ্যালো! আমি আপনার AI পিডিএফ অ্যাসিস্ট্যান্ট। কোনো তথ্য জানতে আগে একটি পিডিএফ ফাইল পাঠান।")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
