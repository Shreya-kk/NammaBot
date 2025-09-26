from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
#from googletrans import Translator

from deep_translator import GoogleTranslator

import google.generativeai as genai
import time

app = Flask(__name__)

# -----------------------------
# Configure Gemini API
# -----------------------------
GEMINI_API_KEY = "AIzaSyC_WXI8fi4EqedWNoaMdbMYocPW16d2ybw"  # Replace with your Gemini API key
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# -----------------------------
# Translator
# -----------------------------
translator_kn_en = GoogleTranslator(source='kn', target='en')
translator_en_kn = GoogleTranslator(source='en', target='kn')


# -----------------------------
# Helper functions
# -----------------------------
def translate_to_english(text, retries=3):
    for attempt in range(retries):
        try:
            return translator_kn_en.translate(text)
        except Exception as e:
            print(f"❌ Translation failed, retrying ({attempt+1}/{retries})", e)
            time.sleep(1)
    return text

def translate_to_kannada(text, retries=3):
    for attempt in range(retries):
        try:
            return translator_en_kn.translate(text)
        except Exception as e:
            print(f"❌ Translation failed, retrying ({attempt+1}/{retries})", e)
            time.sleep(1)
    return text

def get_gemini_response(prompt):
    full_prompt = f"Reply politely and clearly in English. User said: {prompt}"
    try:
        response = gemini_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return "Sorry, I'm unable to respond at the moment."

def get_gemini_response_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return get_gemini_response(prompt)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                wait_time = (attempt + 1) * 10
                print(f"⚠️ Quota exceeded. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                raise e
    return "Sorry, I'm unable to respond at the moment."

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process_audio", methods=["POST"])
def process_audio():
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio file provided."})

    audio_file = request.files["audio_data"]

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        user_text_kn = recognizer.recognize_google(audio, language="kn-IN")
        print("User (Kannada):", user_text_kn)
    except Exception as e:
        return jsonify({"error": "Could not understand audio."})

    greetings_kn = ["ಹಾಯ್", "ನಮಸ್ತೆ", "ನಮಸ್ಕಾರ"]
    exit_words = ["bye", "ಬಾಯ್", "ಎಕ್ಸಿಟ್", "ವಿದಾಯ"]

    if user_text_kn.lower() in exit_words:
        bot_response_kn = "ವಿದಾಯ! 👋"
    elif user_text_kn in greetings_kn:
        bot_response_kn = "ನಮಸ್ತೆ! ನಿಮಗೆ ಸಹಾಯ ಬೇಕೇ?"
    else:
        user_text_en = translate_to_english(user_text_kn)
        bot_response_en = get_gemini_response_with_retry(user_text_en)
        bot_response_kn = translate_to_kannada(bot_response_en)

    return jsonify({"user_text": user_text_kn, "bot_response": bot_response_kn})

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
