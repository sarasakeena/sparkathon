import streamlit as st
from PIL import Image, ImageDraw
import pyttsx3
import speech_recognition as sr
import threading

# -------------------
# Streamlit Setup
st.set_page_config(layout="wide")
st.title("🛒 Smart Store Navigator")

# -------------------
# Text-to-Speech
def speak(text):
    def _speak():
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak).start()

# -------------------
# Store Layout
PRODUCT_LOCATIONS = {
    "milk": {"pos": (100, 130), "section": "Dairy"},
    "butter": {"pos": (120, 130), "section": "Dairy"},
    "eggs": {"pos": (140, 130), "section": "Dairy"},
    "yogurt": {"pos": (160, 130), "section": "Dairy"},
    "vegetables": {"pos": (100, 220), "section": "Grocery"},
    "fruits": {"pos": (130, 220), "section": "Grocery"},
    "bread": {"pos": (160, 220), "section": "Grocery"},
    "jam": {"pos": (180, 220), "section": "Grocery"},
    "snacks": {"pos": (200, 220), "section": "Grocery"},
    "cake": {"pos": (110, 330), "section": "Bakery"},
    "ice creams": {"pos": (130, 330), "section": "Bakery"},
    "juice": {"pos": (150, 330), "section": "Bakery"},
    "biscuits": {"pos": (170, 330), "section": "Bakery"},
    "pet food": {"pos": (280, 120), "section": "Pet Care"},
    "face wash": {"pos": (720, 420), "section": "Health and Beauty"},
    "serum": {"pos": (740, 420), "section": "Health and Beauty"},
    "toner": {"pos": (760, 420), "section": "Health and Beauty"},
    "primer": {"pos": (780, 420), "section": "Health and Beauty"},
}

ENTRANCE = (80, 500)

# -------------------
# Voice Input
st.subheader("🎙️ Voice Input")
voice_query = ""
if st.button("🎤 Start Listening"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = r.listen(source)
    try:
        voice_query = r.recognize_google(audio)
        st.success(f"You said: {voice_query}")
    except Exception as e:
        st.error(f"Error: {e}")

# -------------------
# Text Input
query = st.text_input("🔍 Search for a product:", value=voice_query.lower())
voice_enabled = st.checkbox("🔊 Voice Guidance", value=True)

# -------------------
# Natural Directions Generator
def get_natural_directions(start, middle, end, product_name, section):
    instructions = [f"{product_name.title()} is in the {section} section."]
    dx1 = middle[0] - start[0]
    dy1 = middle[1] - start[1]
    dx2 = end[0] - middle[0]
    dy2 = end[1] - middle[1]

    if dy1 < 0:
        instructions.append("From the entrance, walk up.")
    elif dy1 > 0:
        instructions.append("From the entrance, walk straight ahead.")
    elif dx1 > 0:
        instructions.append("From the entrance, turn right and walk.")
    elif dx1 < 0:
        instructions.append("From the entrance, turn left and walk.")

    if dx2 > 0:
        instructions.append("Then, turn right.")
    elif dx2 < 0:
        instructions.append("Then, turn left.")
    elif dy2 > 0:
        instructions.append("Then, walk forward.")
    elif dy2 < 0:
        instructions.append("Then, walk backward.")

    instructions.append(f"You will reach {product_name.title()}.")
    return instructions

# -------------------
# Main Logic
if query:
    product = query.lower().strip()
    if product in PRODUCT_LOCATIONS:
        dest = PRODUCT_LOCATIONS[product]['pos']
        section = PRODUCT_LOCATIONS[product]['section']
        mid_point = (dest[0], ENTRANCE[1])  # Horizontal-first

        # Load map
        image = Image.open("floorplan.png").convert("RGB")
        draw = ImageDraw.Draw(image)

        # Draw entrance
        draw.ellipse((ENTRANCE[0]-6, ENTRANCE[1]-6, ENTRANCE[0]+6, ENTRANCE[1]+6), fill="green")
        draw.text((ENTRANCE[0]+10, ENTRANCE[1]-10), "Entrance", fill="green")

        # Draw product
        draw.ellipse((dest[0]-6, dest[1]-6, dest[0]+6, dest[1]+6), fill="red")
        draw.text((dest[0]+10, dest[1]-10), product.title(), fill="red")

        # Draw path: entrance → mid → dest
        draw.line([ENTRANCE, mid_point], fill="orange", width=4)
        draw.line([mid_point, dest], fill="orange", width=4)

        # Show map
        st.image(image, caption="🗺️ Store Path to Product", use_container_width=True)

        # Generate directions
        st.subheader("🧭 Directions")
        steps = get_natural_directions(ENTRANCE, mid_point, dest, product, section)

        for step in steps:
            st.markdown(f"- {step}")

        # Speak the whole thing once, in order
        if voice_enabled:
            full_text = " ".join(steps)
            speak(full_text)
    else:
        st.error("❌ Product not found.")
        if voice_enabled:
            speak("Sorry, that product is not available in the store.")
