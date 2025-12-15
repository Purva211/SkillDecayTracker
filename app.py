import streamlit as st
import sqlite3
import math
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="Skill Decay Tracker",
    page_icon="🧠",
    layout="centered"
)
# ================= LOAD CSS =================
def load_css():
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ====================== DATABASE ======================
DB_NAME = "skill_decay.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

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

# ====================== SESSION ======================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

# ====================== UI HELPERS ======================
def card(text):
    st.markdown(
        f"""
        <div class="neon-card">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )

# ====================== AUTH ======================
def register_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username,password) VALUES (?,?)",
                  (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",
              (username, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ====================== LOGIN / REGISTER ======================
if st.session_state.user_id is None:
    st.markdown("""
<h1 style="text-align:center; font-size:42px;">
🧠 Skill Decay Tracker
</h1>
<p style="text-align:center; color:#94a3b8; font-size:18px;">
Track, visualize & protect your skills over time
</p>
""", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            uid = login_user(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u
                st.success("Login successful 🎉")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        ru = st.text_input("New Username")
        rp = st.text_input("New Password", type="password")
        if st.button("Register"):
            if register_user(ru, rp):
                st.success("Registered! Please login 👌")
            else:
                st.error("Username already exists")

    st.stop()

# ====================== SIDEBAR ======================
st.sidebar.success(f"👋 {st.session_state.username}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()

# ====================== ADD / UPDATE SKILL ======================
st.sidebar.header("➕ Add / Update Skill")

skill_name = st.sidebar.text_input("Skill name")
last_practice = st.sidebar.date_input("Last practiced", datetime.date.today())
decay_rate = st.sidebar.slider("Decay rate", 0.01, 0.1, 0.04)

if st.sidebar.button("💾 Save Skill"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO skills (user_id, skill_name, last_practice, decay_rate)
    VALUES (?,?,?,?)
    """, (
        st.session_state.user_id,
        skill_name,
        last_practice.isoformat(),
        decay_rate
    ))
    conn.commit()
    conn.close()
    st.sidebar.success("Skill saved ✅")
    st.rerun()

# ====================== LOAD USER SKILLS ======================
conn = get_connection()
df = pd.read_sql(
    "SELECT * FROM skills WHERE user_id=?",
    conn,
    params=(st.session_state.user_id,)
)
conn.close()

st.markdown("""
<h2 style="text-align:center;">
📊 Your Skill Dashboard
</h2>
<p style="text-align:center; color:#94a3b8;">
Monitor how fast your skills decay & when to practice
</p>
""", unsafe_allow_html=True)


if df.empty:
    card("⚠️ No skills added yet. Add one from the sidebar.")
    st.stop()

skill = st.selectbox("Select a skill", df["skill_name"].tolist())
row = df[df["skill_name"] == skill].iloc[0]

# ====================== DELETE SKILL ======================
if st.button("🗑️ Delete Skill"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM skills WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    st.warning("Skill deleted ❌")
    st.rerun()

# ====================== DECAY CALCULATION ======================
last = datetime.date.fromisoformat(row["last_practice"])
days = (datetime.date.today() - last).days
decay_score = round(100 * math.exp(-row["decay_rate"] * days), 2)

# ====================== STATUS ======================
card(f"""
### 🧠 {skill}
**Skill Strength:** {decay_score}%  
**Days since last practice:** {days}
""")

if decay_score > 70:
    st.success("🟢 Skill is healthy")
elif decay_score > 40:
    st.warning("🟠 Skill needs attention")
else:
    st.error("🔴 Skill is dying — PRACTICE NOW!")

# ====================== GRAPH ======================
x = list(range(days + 1))
y = [100 * math.exp(-row["decay_rate"] * d) for d in x]

fig, ax = plt.subplots()
ax.plot(x, y, linewidth=3)
ax.fill_between(x, y, alpha=0.3)
ax.set_xlabel("Days")
ax.set_ylabel("Skill Strength (%)")
ax.set_title("Skill Decay Curve")

st.pyplot(fig)

# ====================== FUN REMINDERS ======================
if days > 5:
    st.toast("⏰ Your skill is getting rusty… practice today!", icon="⚡")
if decay_score < 40:
    st.toast("🔥 Placement alert! This skill needs love ASAP.", icon="🚨")

# ====================== PRACTICE RECOMMENDATION ======================
st.subheader("🛠️ What should you do now?")
if decay_score > 75:
    card("😎 Chill — revise once a week")
elif decay_score > 40:
    card("🙂 Practice 3x per week")
else:
    card("💀 Emergency mode: DAILY practice")

# ====================== FOOTER ======================
st.markdown("---")
st.caption("🚀 Hackathon Prototype | Skill Decay Tracker | Built by Roshani")
