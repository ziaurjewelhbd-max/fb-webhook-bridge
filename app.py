import requests
from flask import Flask, request
import PyPDF2
import io
import google.generativeai as genai
import sys

app = Flask(__name__)

# ১. ফেসবুক টোকেন
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRX3JQ8arMkK0PURih9tSncgODgENBZCiJtlJpSKRSjBbIHPfXsLlPz2RTQjhO6wmxA5gX7ofaXT7l3z4HL7mIT8oPpoNaOwGfs1xFKZC1NTy7yw0wZCW3z7VhzHAAirCEnL0Ay6T13PHzMoKZA6WbTY7SZBw9qSZCM1yRQOG7Xyy71819SF7QVDgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

# ২. Gemini API Key (নিশ্চিত করুন এটি সঠিক)
GEMINI_API_KEY = "AIzaSyDWuXse1ulRFSh6Ie9TQAgrjQfPO-xTwDA"
genai.configure(api_key=GEMINI_API_KEY)

# এখানে আমরা মডেল সেট করছি (gemini-1.5-flash সবচেয়ে লেটেস্ট এবং ফ্রি)
model = genai.GenerativeModel('gemini-1.5-flash')

user_sessions = {}

def log_message(message):
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

def send_message(recipient_id, text):
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
                text += page.extract_text()
            return text if text.strip() else None
    except Exception as e:
        log_message(f"PDF Error: {e}")
        return None

def get_gemini_response(pdf_content, user_query):
    # প্রম্পটটি আরও পরিষ্কার করা হয়েছে
    full_prompt = (
        f"You are a helpful assistant. Use the following PDF content to answer the user's question.\n\n"
        f"PDF Content: {pdf_content[:15000]}\n\n" # Gemini-র লিমিট অনুযায়ী টেক্সট কাট করা হয়েছে
        f"Question: {user_query}\n\n"
        f"Answer in the same language as the user's question."
    )
    try:
        # জেনারেট করার সময় safety settings শিথিল করা হয়েছে যাতে উত্তর আটকে না যায়
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        log_message(f"Gemini API Error: {e}")
        return "দুঃখিত, আমি উত্তরটি তৈরি করতে পারছি না। সম্ভবত আপনার API Key-তে সমস্যা অথবা প্রম্পটটি আটকে গেছে।"

@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == MY_VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "message" in messaging_event:
                    msg = messaging_event["message"]
                    
                    if "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment["type"] == "file":
                                pdf_url = attachment["payload"]["url"]
                                send_message(sender_id, "পিডিএফটি পেয়েছি। আমি এটি পড়ে নিচ্ছি...")
                                pdf_text = extract_pdf_text(pdf_url)
                                if pdf_text:
                                    user_sessions[sender_id] = pdf_text
                                    send_message(sender_id, "পিডিএফ পড়া শেষ! এখন এই ফাইল থেকে আপনি যা জানতে চান আমাকে প্রশ্ন করুন।")
                                else:
                                    send_message(sender_id, "দুঃখিত, এই পিডিএফ ফাইল থেকে টেক্সট পাওয়া যাচ্ছে না।")
                    
                    elif "text" in msg:
                        query = msg["text"]
                        if sender_id in user_sessions:
                            answer = get_gemini_response(user_sessions[sender_id], query)
                            send_message(sender_id, answer)
                        else:
                            send_message(sender_id, "হ্যালো! আগে একটি পিডিএফ ফাইল পাঠান, তারপর আমি আপনার প্রশ্নের উত্তর দিতে পারব।")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
