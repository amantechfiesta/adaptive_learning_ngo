import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import time
from materials import materials_page
from ratings import show_rating_ui

# =========================================================
# CONFIG & FILE SETUP
# =========================================================
st.set_page_config(page_title="Sahay - Peer Learning", layout="wide")
PROFILE_FILE = "profiles.csv"

# =========================================================
# DATA PERSISTENCE (SAVING PROFILES)
# =========================================================
def load_data():
    """Loads profiles from the CSV file."""
    if os.path.exists(PROFILE_FILE):
        return pd.read_csv(PROFILE_FILE)
    else:
        return pd.DataFrame(columns=["role", "name", "grade", "time", "subjects"])

def save_profile(profile_data):
    """Saves a new profile to the CSV file."""
    df = load_data()
    # Convert list of subjects to string for saving
    profile_data["subjects"] = ", ".join(profile_data["subjects"])
    
    # Add new row
    new_df = pd.concat([df, pd.DataFrame([profile_data])], ignore_index=True)
    new_df.to_csv(PROFILE_FILE, index=False)
    return new_df

# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "profile" not in st.session_state: st.session_state.profile = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "current_match" not in st.session_state: st.session_state.current_match = None

SUBJECTS = ["Mathematics", "English", "Science", "History", "Physics"]

# =========================================================
# MATCHING LOGIC
# =========================================================
def find_match_from_db(current_profile):
    """Finds a match from the saved CSV data."""
    df = load_data()
    
    # Filter: Opposite role and same time slot
    candidates = df[
        (df["role"] != current_profile["role"]) & 
        (df["time"] == current_profile["time"])
    ]
    
    if candidates.empty:
        return None, 0
    
    # Simple scoring: +10 for same grade
    best_candidate = candidates.iloc[0] # Just take the first valid one for prototype
    score = 75 # Mock score for demo
    if best_candidate["grade"] == current_profile["grade"]:
        score += 15
        
    return best_candidate.to_dict(), score

# =========================================================
# APP NAVIGATION
# =========================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Matchmaking", "Learning Materials"])

if page == "Learning Materials":
    materials_page()
    st.stop()

# =========================================================
# MAIN APP FLOW
# =========================================================
st.title("Sahay: Peer Learning Matchmaking System 🎓")

# ---------------------------------------------------------
# STAGE 1: PROFILE SETUP (SAVES TO CSV)
# ---------------------------------------------------------
if st.session_state.stage == 1:
    st.header("Step 1: Create Profile")
    st.info("ℹ️ Your profile will be saved securely.")

    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("Role", ["Student", "Teacher"])
        name = st.text_input("Full Name")
    with col2:
        grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

    subjects = st.multiselect("Select Subjects (Strong for Mentor / Weak for Student)", SUBJECTS)

    if st.button("Save Profile & Find Match", type="primary"):
        if not name:
            st.error("Please enter a name")
        else:
            profile = {
                "role": role,
                "name": name,
                "grade": grade,
                "time": time_slot,
                "subjects": subjects
            }
            
            # SAVE TO DATABASE (CSV)
            save_profile(profile)
            st.session_state.profile = profile
            st.toast("Profile Saved Successfully! 💾")
            
            time.sleep(1)
            st.session_state.stage = 2
            st.rerun()

# ---------------------------------------------------------
# STAGE 2: MATCH RESULTS
# ---------------------------------------------------------
elif st.session_state.stage == 2:
    st.header("Step 2: Match Results")
    
    with st.spinner("Searching database for peers..."):
        time.sleep(1.5)
        # Find match using the CSV data
        best_mentor, score = find_match_from_db(st.session_state.profile)

    if best_mentor is not None:
        st.success(f"Match Found! Compatibility Score: {score}/100")
        
        # Determine who is who based on current user role
        if st.session_state.profile["role"] == "Student":
            mentor_name = best_mentor["name"]
            mentee_name = st.session_state.profile["name"]
        else:
            mentor_name = st.session_state.profile["name"]
            mentee_name = best_mentor["name"]

        st.session_state.current_match = {
            "Mentor": mentor_name,
            "Mentee": mentee_name,
            "Score": score
        }
        
        col1, col2 = st.columns(2)
        col1.metric("Mentor", mentor_name)
        col2.metric("Mentee", mentee_name)
        
        if st.button("Start Live Session"):
            st.session_state.stage = 3
            st.rerun()
    else:
        st.warning("No live match found. You are the first in this time slot!")
        st.info("We have saved your profile. Please check back later when more students register.")
        if st.button("Back to Home"):
            st.session_state.stage = 1
            st.rerun()

# ---------------------------------------------------------
# STAGE 3: LIVE SESSION (AI + TEACHER SUPPORT)
# ---------------------------------------------------------
elif st.session_state.stage == 3:
    st.header("Live Learning Session 💬")
    
    # 1. SETUP API
    api_ready = False
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        api_ready = True
    else:
        st.error("⚠️ API Key missing. Chatbot will not work.")

    # 2. CHAT INTERFACE
    col_chat, col_tools = st.columns([2, 1])

    with col_chat:
        st.subheader("Discussion")
        
        # Init History
        if not st.session_state.chat_history:
            intro = f"**System:** Connected {st.session_state.current_match['Mentor']} and {st.session_state.current_match['Mentee']}."
            st.session_state.chat_history.append(("assistant", intro))

        # Display History
        for role, text in st.session_state.chat_history:
            # Differentiate Teacher Messages
            if "👩‍🏫" in text:
                with st.chat_message("assistant", avatar="👩‍🏫"):
                    st.markdown(text)
            else:
                with st.chat_message(role):
                    st.markdown(text)

        # Input
        if api_ready:
            if prompt := st.chat_input("Type your message..."):
                st.session_state.chat_history.append(("user", prompt))
                st.rerun()

    # 3. SIDEBAR TOOLS
    with col_tools:
        st.subheader("Session Tools")
        
        # --- FEATURE: TEACHER SUPPORT ---
        st.write("Need help? Stuck on a problem?")
        if st.button("👩‍🏫 Call Faculty Support", type="secondary"):
            st.toast("Faculty Notified! Joining chat...")
            time.sleep(1)
            # Inject Teacher Message
            teacher_msg = "👩‍🏫 **Faculty Support:** Hi there! I've joined the session. I see you're discussing this topic. How can I clarify things for you?"
            st.session_state.chat_history.append(("assistant", teacher_msg))
            st.rerun()
        
        st.divider()
        
        # --- FEATURE: AI ASSISTANT ---
        if st.button("🤖 Ask AI for Help"):
            if st.session_state.chat_history:
                last_msg = st.session_state.chat_history[-1][1]
                with st.spinner("AI is analyzing context..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        # Contextual prompt
                        response = model.generate_content(f"You are a helpful tutor. The student said: '{last_msg}'. Give a short, encouraging hint.")
                        st.session_state.chat_history.append(("assistant", f"🤖 **AI Hint:** {response.text}"))
                        st.rerun()
                    except:
                        st.error("AI Error")

        st.divider()
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()

# ---------------------------------------------------------
# STAGE 4: FEEDBACK
# ---------------------------------------------------------
elif st.session_state.stage == 4:
    show_rating_ui()
    if st.button("Finish"):
        st.session_state.stage = 1
        st.session_state.chat_history = []
        st.rerun()
