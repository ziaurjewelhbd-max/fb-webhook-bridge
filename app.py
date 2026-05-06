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

# ২. আপনার Gemini API Key (এখানে নিজের Key টি বসান)
GEMINI_API_KEY = "AIzaSyA9CBjyzl-8XD-VQzbPo8jyWhxFl90VUFI"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# ইউজার অনুযায়ী ডাটা রাখার মেমোরি
user_sessions = {}

def log_message(message):
    """Render লগে তাৎক্ষণিক লেখা দেখানোর জন্য ফাংশন"""
    print(f"DEBUG: {message}", file=sys.stderr, flush=True)

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    response = requests.post(url, json=payload)
    log_message(f"Sent Reply Status: {response.status_code}")

def extract_pdf_text(pdf_url):
    try:
        log_message(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url)
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            log_message(f"Extracted {len(text)} characters from PDF")
            return text
    except Exception as e:
        log_message(f"Error extracting PDF: {str(e)}")
        return None

def get_gemini_response(pdf_content, user_query):
    log_message(f"Asking Gemini about: {user_query}")
    prompt = f"Context from PDF: {pdf_content}\n\nUser Question: {user_query}\n\nPlease answer the question based on the provided PDF context. If the answer is not in the PDF, say you don't know. Answer in the same language as the user."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log_message(f"Gemini Error: {str(e)}")
        return "দুঃখিত, Gemini AI এখন উত্তর দিতে পারছে না।"

@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == MY_VERIFY_TOKEN:
        log_message("Webhook Verified Successfully")
        return request.args.get("hub.challenge"), 200
    return "Failed", 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    log_message(f"Incoming Event: {data}") # পুরো ডাটা লগে দেখাবে

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                
                if "message" in messaging_event:
                    msg = messaging_event["message"]
                    
                    # যদি পিডিএফ ফাইল পাঠায়
                    if "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment["type"] == "file":
                                log_message(f"PDF Received from {sender_id}")
                                url = attachment["payload"]["url"]
                                send_message(sender_id, "পিডিএফটি পেয়েছি। আমি এটি পড়ে নিচ্ছি...")
                                pdf_text = extract_pdf_text(url)
                                if pdf_text:
                                    user_sessions[sender_id] = pdf_text
                                    send_message(sender_id, "পিডিএফ পড়া শেষ! এখন এই ফাইল থেকে আপনি যা জানতে চান আমাকে প্রশ্ন করুন।")
                    
                    # যদি টেক্সট মেসেজ পাঠায়
                    elif "text" in msg:
                        query = msg["text"]
                        log_message(f"Text Message from {sender_id}: {query}")
                        
                        if sender_id in user_sessions:
                            answer = get_gemini_response(user_sessions[sender_id], query)
                            send_message(sender_id, answer)
                        else:
                            send_message(sender_id, "হ্যালো! আমি আপনার AI পিডিএফ অ্যাসিস্ট্যান্ট। কোনো তথ্য জানতে আগে একটি পিডিএফ ফাইল পাঠান।")
                
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
