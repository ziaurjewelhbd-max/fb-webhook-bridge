import os
import requests
from flask import Flask, request
import PyPDF2
import io
import google.generativeai as genai
import sys

app = Flask(__name__)

# ১. ফেসবুক ক্রেডেনশিয়াল (আগের মতোই থাকবে)
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRX3JQ8arMkK0PURih9tSncgODgENBZCiJtlJpSKRSjBbIHPfXsLlPz2RTQjhO6wmxA5gX7ofaXT7l3z4HL7mIT8oPpoNaOwGfs1xFKZC1NTy7yw0wZCW3z7VhzHAAirCEnL0Ay6T13PHzMoKZA6WbTY7SZBw9qSZCM1yRQOG7Xyy71819SF7QVDgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

# ২. Gemini API Key (এখন আমরা Render থেকে নিচ্ছি)
# os.environ.get ব্যবহার করলে এটি Render-এ সেট করা ভ্যালুটি খুঁজে নেবে
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # আমরা ১.৫ ফ্ল্যাশ মডেলটি ব্যবহার করছি যা দ্রুত এবং নির্ভুল
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    # যদি Key খুঁজে না পায় তবে এটি লগে দেখাবে
    print("CRITICAL ERROR: GEMINI_API_KEY is not set in Render!")

user_sessions = {}

def log_message(message):
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

def send_fb_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

def extract_pdf_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text if text.strip() else None
    except Exception as e:
        log_message(f"PDF Error: {e}")
        return None

@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == MY_VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]
                if "message" in event:
                    msg = event["message"]
                    
                    # যদি ইউজার ফাইল পাঠায়
                    if "attachments" in msg:
                        for attach in msg["attachments"]:
                            if attach["type"] == "file":
                                send_fb_message(sender_id, "পিডিএফটি পেয়েছি। একটু সময় দিন...")
                                pdf_text = extract_pdf_text(attach["payload"]["url"])
                                if pdf_text:
                                    user_sessions[sender_id] = pdf_text
                                    send_fb_message(sender_id, "পিডিএফ পড়া শেষ! এখন প্রশ্ন করুন।")
                                else:
                                    send_fb_message(sender_id, "পিডিএফ থেকে লেখা পড়তে পারছি না।")
                    
                    # যদি ইউজার প্রশ্ন করে
                    elif "text" in msg:
                        query = msg["text"]
                        if sender_id in user_sessions:
                            try:
                                # Gemini থেকে উত্তর নেওয়া
                                response = model.generate_content(
                                    f"Based on this PDF: {user_sessions[sender_id][:15000]}\nAnswer this: {query}"
                                )
                                send_fb_message(sender_id, response.text)
                            except Exception as e:
                                log_message(f"Gemini Error: {e}")
                                send_fb_message(sender_id, "দুঃখিত, উত্তর দিতে সমস্যা হচ্ছে।")
                        else:
                            send_fb_message(sender_id, "হ্যালো! আগে একটি পিডিএফ ফাইল পাঠান।")
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
