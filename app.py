import streamlit as st
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
from streamlit_folium import st_folium
import folium

DATA_DIR = Path("data")
VENUES_CSV = DATA_DIR / "venues.csv"
FEEDBACK_CSV = DATA_DIR / "feedback.csv"

SCHOOL_CENTER = (11.067095, 76.916370)  # Yuvabharathi coordinates
SCHOOL_NAME = "Yuvabharathi Public School"
APP_TITLE = "Project Day 2025 Navigator"

st.set_page_config(page_title=APP_TITLE, page_icon="🎒", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .venue-card { padding: 0.8rem 1rem; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 8px; }
    .pill { background:#eef2ff; color:#3730a3; padding:2px 8px; border-radius:999px; font-size:12px; }
    </style>
""", unsafe_allow_html=True)

DATA_DIR.mkdir(exist_ok=True)
if not FEEDBACK_CSV.exists():
    pd.DataFrame(columns=["timestamp","visitor_name","visitor_phone","venue_id","venue_name","rating","comments"]).to_csv(FEEDBACK_CSV, index=False)

@st.cache_data
def load_venues():
    return pd.read_csv(VENUES_CSV)

def save_feedback(record: dict):
    df = pd.read_csv(FEEDBACK_CSV)
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(FEEDBACK_CSV, index=False)

def valid_phone(p: str):
    return len(p) == 10 and p in "6789" and p.isdigit()

def send_otp_stub(phone: str) -> str:
    otp = "123456"
    st.session_state["_otp_sent"] = otp
    st.session_state["_otp_time"] = time.time()
    return otp

def verify_otp_stub(otp_input: str) -> bool:
    return otp_input == st.session_state.get("_otp_sent")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "name": "", "phone": ""}

def login_view():
    st.title(APP_TITLE)
    st.caption(SCHOOL_NAME)
    st.subheader("Visitor Login")

    name = st.text_input("Full Name")
    phone = st.text_input("Phone Number (10 digits)")
    use_otp = st.toggle("Enable OTP verification (demo)")

    col1, col2 = st.columns([1,1])
    with col1:
        proceed = st.button("Continue", type="primary")
    with col2:
        st.write("")

    if proceed:
        if not name.strip():
            st.error("Please enter name.")
            return
        if not valid_phone(phone):
            st.error("Enter a valid 10-digit mobile number starting with 6-9.")
            return
        if use_otp:
            send_otp_stub(phone)
            st.info("OTP sent (demo: 123456). Please verify below.")
            otp_in = st.text_input("Enter OTP", type="password")
            if st.button("Verify OTP"):
                if verify_otp_stub(otp_in):
                    st.success("OTP verified.")
                    st.session_state.auth = {"logged_in": True, "name": name.strip(), "phone": phone}
                    st.rerun()
                else:
                    st.error("Incorrect OTP.")
        else:
            st.session_state.auth = {"logged_in": True, "name": name.strip(), "phone": phone}
            st.rerun()

def app_header():
    left, right = st.columns([3,1])
    with left:
        st.subheader(f"Welcome, {st.session_state.auth['name']}")
    with right:
        if st.button("Logout"):
            st.session_state.auth = {"logged_in": False, "name": "", "phone": ""}
            st.rerun()

def venue_browser(df):
    st.markdown("### Explore Venues")
    q = st.text_input("Search venue or building")
    if q:
        m = df["name"].str.contains(q, case=False) | df["building"].str.contains(q, case=False) | df["desc"].str.contains(q, case=False)
        df = df[m]

    cols = st.columns(2)
    selections = {}
    for i, row in df.iterrows():
        with cols[i % 2]:
            with st.container():
                st.markdown(f"<div class='venue-card'><b>{row['name']}</b><br><span class='pill'>{row['building']}</span> · {row['floor']}<br><small>{row['desc']}</small></div>", unsafe_allow_html=True)
                selections[row["id"]] = st.button(f"Navigate to {row['name']}", key=f"nav_{row['id']}")
    chosen = None
    for vid, clicked in selections.items():
        if clicked:
            chosen = int(vid)
            break
    return chosen

def navigation_map(df, venue_id):
    venue = df[df["id"] == venue_id].iloc
    st.markdown("### Navigation")
    st.write(f"Destination: {venue['name']} · {venue['building']} · {venue['floor']}")
    center = SCHOOL_CENTER

    m = folium.Map(location=center, zoom_start=18, tiles="OpenStreetMap")
    folium.Marker(center, tooltip=SCHOOL_NAME, icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
    dest = (venue["lat"], venue["lon"])
    folium.Marker(dest, tooltip=venue["name"], icon=folium.Icon(color="red", icon="flag")).add_to(m)
    folium.PolyLine([center, dest], color="green", weight=4, opacity=0.7).add_to(m)

    st_folium(m, width=1000, height=500)
    arrived = st.button("Mark Arrived")
    return venue, arrived

def feedback_form(venue):
    st.markdown("### Feedback")
    rating = st.slider("Rating", 1, 5, 5)
    comments = st.text_area("Comments (optional)")
    if st.button("Submit Feedback", type="primary"):
        rec = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "visitor_name": st.session_state.auth["name"],
            "visitor_phone": st.session_state.auth["phone"],
            "venue_id": int(venue["id"]),
            "venue_name": venue["name"],
            "rating": int(rating),
            "comments": comments.strip()
        }
        save_feedback(rec)
        st.success("Thank you! Feedback submitted.")
        st.balloons()

def main_app():
    app_header()
    df = load_venues()
    tab1, tab2, tab3 = st.tabs(["Browse", "Map", "Feedback"])
    with tab1:
        choice = venue_browser(df)
        if choice is not None:
            st.session_state["selected_venue"] = choice
            st.switch_page("app.py")
    with tab2:
        if "selected_venue" not in st.session_state:
            st.info("Choose a venue in Browse to start navigation.")
        else:
            venue, arrived = navigation_map(df, st.session_state["selected_venue"])
            if arrived:
                st.session_state["arrived_venue"] = int(venue["id"])
                st.success(f"Arrived at {venue['name']}. Go to Feedback tab.")
    with tab3:
        if "arrived_venue" in st.session_state:
            v = load_venues()
            venue = v[v["id"] == st.session_state["arrived_venue"]].iloc
            feedback_form(venue)
        else:
            st.info("Mark Arrived in the Map tab to give feedback.")

if not st.session_state.auth["logged_in"]:
    login_view()
else:
    main_app()

import re, streamlit as st
st.title("Attendee details")
name = st.text_input("Name", placeholder="Enter your full name")
phone = st.text_input("Phone", placeholder="10-digit mobile")
if st.button("Continue"):
if not name or not phone:
st.error("Both name and phone are required.")
elif not re.fullmatch(r"[A-Za-z ]{1,50}", name):
st.error("Name must have only letters and spaces.")
elif not re.fullmatch(r"\d{10}", phone):
st.error("Phone must be exactly 10 digits.")
else:
st.success("Thanks! Proceeding...")