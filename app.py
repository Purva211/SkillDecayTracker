import streamlit as st
import sqlite3
import math
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Skill Decay Tracker", layout="centered")

# ---------------- DATABASE ----------------
def get_connection():
    return sqlite3.connect("skill_decay.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        skill_name TEXT,
        last_practice TEXT,
        decay_rate REAL,
        UNIQUE(user_id, skill_name)
    )
    """)

    conn.commit()
    conn.close()

create_tables()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------- AUTH ----------------
def register(username, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?,?)",
                  (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()
    return user

# ---------------- LOGIN / REGISTER UI ----------------
if not st.session_state.logged_in:
    st.title("🔐 Skill Decay Tracker")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.success("Login successful 🎉")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        ru = st.text_input("New Username")
        rp = st.text_input("New Password", type="password")
        if st.button("Register"):
            if register(ru, rp):
                st.success("Registered successfully 🎉 Now login")
            else:
                st.error("Username already exists")

    st.stop()

# ---------------- LOGOUT ----------------
st.sidebar.success("Logged in")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.rerun()

# ---------------- APP MAIN ----------------
st.title("🧠 Skill Decay Tracker")
st.write("Track how your skills decay and get smart practice guidance.")

conn = get_connection()
c = conn.cursor()

# ---------------- ADD / UPDATE SKILL ----------------
st.sidebar.subheader("➕ Add / Update Skill")

skill_name = st.sidebar.text_input("Skill name")
last_date = st.sidebar.date_input("Last practiced date", datetime.date.today())
decay_rate = st.sidebar.slider("Decay rate", 0.01, 0.1, 0.04)

if st.sidebar.button("Save Skill"):
    c.execute("""
    INSERT INTO skills (user_id, skill_name, last_practice, decay_rate)
    VALUES (?,?,?,?)
    ON CONFLICT(user_id, skill_name)
    DO UPDATE SET last_practice=excluded.last_practice,
                  decay_rate=excluded.decay_rate
    """, (
        st.session_state.user_id,
        skill_name,
        last_date.isoformat(),
        decay_rate
    ))
    conn.commit()
    st.sidebar.success("Skill saved / updated ✅")
    st.rerun()

# ---------------- LOAD USER SKILLS ----------------
c.execute("SELECT skill_name, last_practice, decay_rate FROM skills WHERE user_id=?",
          (st.session_state.user_id,))
rows = c.fetchall()

if not rows:
    st.info("No skills added yet.")
    st.stop()

skills = {r[0]: {"last_practice": r[1], "decay_rate": r[2]} for r in rows}

# ---------------- SELECT SKILL ----------------
skill = st.selectbox("Select a skill", list(skills.keys()))
last_practice = datetime.date.fromisoformat(skills[skill]["last_practice"])
decay_rate = skills[skill]["decay_rate"]

# ---------------- DELETE SKILL ----------------
if st.button("❌ Delete Skill"):
    c.execute("DELETE FROM skills WHERE user_id=? AND skill_name=?",
              (st.session_state.user_id, skill))
    conn.commit()
    st.warning("Skill deleted")
    st.rerun()

# ---------------- DECAY LOGIC ----------------
today = datetime.date.today()
days_passed = (today - last_practice).days
decay_score = round(100 * math.exp(-decay_rate * days_passed), 2)

# ---------------- DECAY STATUS ----------------
st.subheader("📉 Skill Strength")
st.metric("Current Skill Level", f"{decay_score}%")

if decay_score > 70:
    st.success("🟢 Healthy skill")
elif decay_score > 40:
    st.warning("🟠 Needs practice")
else:
    st.error("🔴 Skill decay critical")

st.info("Decay shows how skill strength reduces when not practiced.")

# ---------------- GRAPH ----------------
days = list(range(0, days_passed + 1))
values = [100 * math.exp(-decay_rate * d) for d in days]

fig, ax = plt.subplots()
ax.plot(days, values, linewidth=3)
ax.fill_between(days, values, alpha=0.3)
ax.set_xlabel("Days since last practice")
ax.set_ylabel("Skill strength (%)")
ax.set_title("Skill Decay Curve")

st.pyplot(fig)

# ---------------- FUN REMINDERS ----------------
if days_passed > 7:
    st.toast("📢 Your skill misses you. Time to practice!", icon="⏰")

if decay_score < 40:
    st.toast("🔥 Skill decay alert! Practice now.", icon="🚨")

# ---------------- PRACTICE RECOMMENDATION ----------------
st.subheader("🛠️ Practice Recommendation")

if decay_score > 75:
    st.write("😎 Light revision once a week")
elif decay_score > 40:
    st.write("🙂 Practice 3 times a week")
else:
    st.write("🚨 Daily intensive practice needed")

# ---------------- ADJACENT SKILLS ----------------
st.subheader("🧭 Adjacent Skills")

adjacent = {
    "Python": ["Automation", "Data Analysis", "Machine Learning"],
    "Machine Learning": ["Deep Learning", "MLOps"],
    "Web Development": ["React", "APIs"]
}

for s in adjacent.get(skill, ["Problem Solving", "System Design"]):
    st.write("•", s)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("🚀 Hackathon Prototype | Skill Decay Tracker")

conn.close()
