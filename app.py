import requests
from flask import Flask, request
import PyPDF2
import io
import google.generativeai as genai
import sys

app = Flask(__name__)

# ১. আপনার ফেসবুক ডিটেইলস
PAGE_ACCESS_TOKEN = "EAAe9LTMlolcBRX3JQ8arMkK0PURih9tSncgODgENBZCiJtlJpSKRSjBbIHPfXsLlPz2RTQjhO6wmxA5gX7ofaXT7l3z4HL7mIT8oPpoNaOwGfs1xFKZC1NTy7yw0wZCW3z7VhzHAAirCEnL0Ay6T13PHzMoKZA6WbTY7SZBw9qSZCM1yRQOG7Xyy71819SF7QVDgZDZD"
MY_VERIFY_TOKEN = "my_pdf_bot_token"

# ২. আপনার Gemini API Key
GEMINI_API_KEY = "AIzaSyDkJZHIKx4k4glzI17PBr4zwzv2FckhYfc"
genai.configure(api_key=GEMINI_API_KEY)

# ইউজার সেশন ডাটা (RAM-এ সেভ থাকবে)
user_sessions = {}

def log_message(message):
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        log_message(f"Send Error: {e}")

def extract_pdf_text(pdf_url):
    try:
        response = requests.get(pdf_url)
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
            return text if text.strip() else None
    except Exception as e:
        log_message(f"PDF Error: {e}")
        return None

def get_gemini_response(pdf_content, user_query):
    # একাধিক মডেল ট্রাই করার লজিক যাতে ৪MDL না আসে
    models_to_try = ['gemini-1.5-flash', 'gemini-pro']
    
    prompt = (
        f"You are a helpful AI assistant. Use the following PDF content to answer the user's question.\n\n"
        f"PDF Content: {pdf_content[:20000]}\n\n"
        f"User Question: {user_query}\n\n"
        f"Answer in the language of the user's question (e.g., if Bengali, answer in Bengali)."
    )

    for model_name in models_to_try:
        try:
            log_message(f"Trying Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            log_message(f"Error with {model_name}: {str(e)}")
            continue # এই মডেল কাজ না করলে পরেরটা ট্রাই করবে
    
    return "দুঃখিত, আমি এই মুহূর্তে উত্তর দিতে পারছি না। আপনার API Key অথবা Google AI Studio-তে কোটা (Quota) শেষ হয়ে থাকতে পারে।"

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
                    
                    # পিডিএফ ফাইল ডিটেকশন
                    if "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment["type"] == "file":
                                pdf_url = attachment["payload"]["url"]
                                send_message(sender_id, "পিডিএফটি পেয়েছি। আমি এটি পড়ে নিচ্ছি...")
                                pdf_text = extract_pdf_text(pdf_url)
                                if pdf_text:
                                    user_sessions[sender_id] = pdf_text
                                    send_message(sender_id, "পিডিএফ পড়া শেষ! এখন এই ফাইল সম্পর্কে আমাকে প্রশ্ন করুন।")
                                else:
                                    send_message(sender_id, "দুঃখিত, এই পিডিএফ থেকে কোনো টেক্সট পাওয়া যায়নি।")
                    
                    # প্রশ্ন ডিটেকশন
                    elif "text" in msg:
                        query = msg["text"]
                        if sender_id in user_sessions:
                            answer = get_gemini_response(user_sessions[sender_id], query)
                            send_message(sender_id, answer)
                        else:
                            send_message(sender_id, "হ্যালো! আমি আপনার AI অ্যাসিস্ট্যান্ট। আগে একটি পিডিএফ ফাইল পাঠান, তারপর আমি উত্তর দিতে পারব।")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
