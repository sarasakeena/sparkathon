import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from collections import deque
import pyttsx3
import threading
import speech_recognition as sr
from PIL import Image
import os

# -----------------------------
# Text-to-Speech

def speak(text):
    def _speak():
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak).start()

# -----------------------------
# Store setup (now with sections)
store_layout = {
    'A1': {'product': 'Milk', 'section': 'Dairy'},
    'A2': {'product': 'Bread', 'section': 'Bakery'},
    'B1': {'product': 'Oat Milk', 'section': 'Dairy'},
    'B2': {'product': 'Cereal', 'section': 'Grocery'},
    'C3': {'product': 'Soap', 'section': 'Health & Beauty'},
    'D4': {'product': 'Toothpaste', 'section': 'Health & Beauty'},
    'E1': {'product': 'Shampoo', 'section': 'Health & Beauty'},
    'F5': {'product': 'Detergent', 'section': 'Cleaning'},
    'G6': {'product': 'Eggs', 'section': 'Grocery'},
    'H7': {'product': 'Butter', 'section': 'Dairy'},
    'I8': {'product': 'Rice', 'section': 'Grocery'},
    'J9': {'product': 'Lentils', 'section': 'Grocery'},
}
store_grid = {
    'A1': (0, 0), 'A2': (0, 1), 'B1': (1, 0), 'B2': (1, 1),
    'C3': (2, 2), 'D4': (3, 3), 'E1': (4, 0), 'F5': (5, 4),
    'G6': (6, 5), 'H7': (7, 6), 'I8': (8, 7), 'J9': (9, 8)
}
congestion = [(3, 3), (4, 0), (6, 5)]

# -----------------------------
# Convert store cell to lat/lng
base_lat, base_lng = 13.0674, 80.2376

def cell_to_latlng(cell):
    y, x = store_grid[cell]
    return (base_lat - 0.0001 * y, base_lng + 0.0001 * x)

# -----------------------------
# Pathfinding (BFS)
def bfs(start, goal, obstacles):
    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == goal:
            return path
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < 10 and 0 <= ny < 10 and (nx, ny) not in visited and (nx, ny) not in obstacles:
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [(nx, ny)]))
    return []

# -----------------------------
# Directions

def get_directions(path):
    dir_map = {(1, 0): "⬇️ Go down", (-1, 0): "⬆️ Go up", (0, 1): "➡️ Turn right", (0, -1): "⬅️ Turn left"}
    directions = []
    for i in range(1, len(path)):
        dx = path[i][0] - path[i - 1][0]
        dy = path[i][1] - path[i - 1][1]
        directions.append(dir_map.get((dx, dy), "🔄 Unknown"))
    return directions

# -----------------------------
# UI
st.set_page_config(layout="wide")
st.title("🛒 Smart Aisle Nav — Walmart Indoor Navigation")

query = ""
if st.button("🎤 Voice Input"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Listening...")
        audio = r.listen(source)
    try:
        query = r.recognize_google(audio)
        st.success(f"You said: {query}")
    except Exception as e:
        st.error(f"Voice Error: {e}")

query = st.text_input("🔍 Search product or aisle:", value=query)
voice = st.checkbox("🔊 Voice Guidance")

if query:
    q = query.strip().upper()
    item, location, section = None, None, None
    for loc, info in store_layout.items():
        if q == loc or q.lower() in info['product'].lower():
            item = info['product']
            location = loc
            section = info['section']
            break

    if not location:
        st.error("❌ Product not found.")
        if voice: speak("Product not found.")
        st.stop()

    st.success(f"{item} found in the {section} section")
    if voice: speak(f"{item} found in the {section} section")

    start = (0, 0)
    goal = store_grid[location]
    path = bfs(start, goal, congestion)

    if not path:
        st.error("No path due to congestion.")
        if voice: speak("Route blocked due to congestion.")
        st.stop()

    # Directions
    st.subheader("🧭 Directions")
    steps = get_directions(path)
    for step in steps:
        st.markdown(f"- {step}")
    if voice:
        speak("Starting route")
        for step in steps:
            speak(step)
        speak("Reached destination")

    # Map with image overlay
    m = folium.Map(location=cell_to_latlng('A1'), zoom_start=20, tiles="CartoDB Positron")

    # Floorplan overlay
    image_path = "floorplan.png"
    image_bounds = [[13.0666, 80.2370], [13.0674, 80.2380]]
    if os.path.exists(image_path):
        ImageOverlay(
            name="Walmart Layout",
            image=image_path,
            bounds=image_bounds,
            opacity=0.6,
            interactive=True,
            cross_origin=False,
        ).add_to(m)

    # Entrance and destination
    folium.Marker(cell_to_latlng('A1'), tooltip="🟢 Entrance", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(cell_to_latlng(location), tooltip=f"🔵 {item}", icon=folium.Icon(color='blue')).add_to(m)

    # Congestion
    for cell in congestion:
        for loc, (y, x) in store_grid.items():
            if (y, x) == cell:
                folium.CircleMarker(cell_to_latlng(loc), radius=6, color='red', fill=True, fill_opacity=0.6).add_to(m)

    # Path
    path_coords = []
    for p in path:
        for loc, (y, x) in store_grid.items():
            if (y, x) == p:
                path_coords.append(cell_to_latlng(loc))
                break
    folium.PolyLine(path_coords, color='orange', weight=5, tooltip="Path").add_to(m)

    # Show Map
    st.subheader("🗺️ Interactive Indoor Map")
    st_folium(m, width=800, height=600)
