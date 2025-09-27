import os
import time
from flask import Flask, render_template, request, session, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()
print("Gemini API Key Loaded:", os.getenv("GEMINI_API_KEY"))

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = "kannada_chatbot_secret"

# Initialize translator
translator = GoogleTranslator(source='auto', target='en')

def get_gemini_response(prompt):
    full_prompt = (
        f"You are an expert agriculture assistant. "
        f"Answer ONLY questions related to farming, crops, soil, fertilizers, irrigation, "
        f"plant diseases, animal husbandry, and ANY type of animal health (including farm animals and pets). "
        f"animal health, and rural agriculture practices. "
        f"If the question is not related to agriculture, reply politely in Kannada: "
        f"'ಕ್ಷಮಿಸಿ, ನಾನು ಕೃಷಿ ಮತ್ತು ಪಶುಪಾಲನೆಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಶ್ನೆಗಳಿಗೆ ಮಾತ್ರ ಉತ್ತರ ನೀಡುತ್ತೇನೆ.'\n\n"
        f"When the user asks about a disease or treatment, "
        f"always mention the common medicine, pesticide, or veterinary treatment generally used. "    
        f"User asked: {prompt}\n\n"
        f"Answer in **Kannada only**, clear, natural, and grammatically correct. "
        f"Keep the answer short (max 3 sentences)."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception:
        return "ಕ್ಷಮಿಸಿ, ನಾನು ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಲಾಗುವುದಿಲ್ಲ."

def get_gemini_response_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return get_gemini_response(prompt)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)
            else:
                raise e
    return "ಕ್ಷಮಿಸಿ, ನಾನು ಪ್ರಸ್ತುತ ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಲು ಸಾಧ್ಯವಿಲ್ಲ."

def translate_to_english(text, retries=3):
    for attempt in range(retries):
        try:
            return GoogleTranslator(source="kn", target="en").translate(text)
        except Exception as e:
            time.sleep(1)
    return text

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_text = request.json.get("text")
    lang = request.json.get("lang", "en")  # Default to English
    
    greetings_kn = ["ಹಾಯ್", "ನಮಸ್ತೆ", "ನಮಸ್ಕಾರ", "ಹಲೋ"]
    
    if "bye" in user_text.lower() or "ವಿದಾಯ" in user_text or "ಬೈ" in user_text.lower():
        bot_response_kn = "ವಿದಾಯ! 👋 ಮತ್ತೆ ಸಂಪರ್ಕಿಸಿ."
    elif any(greeting in user_text for greeting in greetings_kn):
        bot_response_kn = "ನಮಸ್ತೆ! ನಾನು ಕನ್ನಡ ಕೃಷಿ ಸಹಾಯಕ. ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
    else:
        # If input is in Kannada, translate to English for Gemini
        if lang == "kn":
            user_text_en = translate_to_english(user_text)
        else:
            user_text_en = user_text
            
        # Get response from Gemini
        bot_response_kn = get_gemini_response_with_retry(user_text_en)

    return {"reply": bot_response_kn}

if __name__ == "__main__":
    app.run(debug=True)
