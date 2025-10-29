import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import base64

# -------------------------------------------------
# PAGE SETUP
st.set_page_config(page_title="MMCCCL Onboarding Document Review & Sign", layout="wide")

# --- Custom Header Layout ---
st.markdown("""
    <style>
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 2px solid #eee;
        margin-bottom: 1rem;
    }
    .main-header {
        color: #0072b2;
        font-size: 2.2rem;
        font-weight: 400;
        text-align: right;
    }
    .logo-left {
        width: 300px;
        max-height: 150px;
        object-fit: contain;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header / Logo ---
logo_path = "mmcccl_logo.png"
logo_html = ""
if Path(logo_path).exists():
    logo_base64 = base64.b64encode(open(logo_path, "rb").read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo-left" />'

st.markdown(f"""
<div class="header-container">
  <div>{logo_html}</div>
  <div><h1 class="main-header">MMCCCL Onboarding Document Review & Sign</h1></div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONFIG
ROOT = Path("docs")
CATEGORIES = {
    "Standard SOPs": ROOT / "sop",
    "Technical Documents": ROOT / "technical",
    "Safety Policies": ROOT / "safety",
}

SIGNATURES_DIR = Path("signatures")
SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_PROGRESS_CSV = SIGNATURES_DIR / "review_progress.csv"
SIGNATURE_CSV = SIGNATURES_DIR / "review_signatures.csv"
LAST_USER_CSV = SIGNATURES_DIR / "last_user.csv"

# Ensure folders exist
for folder in CATEGORIES.values():
    folder.mkdir(parents=True, exist_ok=True)

# Initialize files
if not REVIEW_PROGRESS_CSV.exists():
    pd.DataFrame(columns=["name", "email", "category", "file", "reviewed", "timestamp"]).to_csv(REVIEW_PROGRESS_CSV, index=False)

if not SIGNATURE_CSV.exists():
    pd.DataFrame(columns=["timestamp_utc", "timestamp_local", "name", "email", "role", "category", "reviewed_files"]).to_csv(SIGNATURE_CSV, index=False)

if not LAST_USER_CSV.exists():
    pd.DataFrame(columns=["name", "email", "role"]).to_csv(LAST_USER_CSV, index=False)

# -------------------------------------------------
# HELPERS
def list_files(folder: Path):
    return [p for p in sorted(folder.rglob("*.pdf")) if p.is_file()]

def get_progress():
    try:
        return pd.read_csv(REVIEW_PROGRESS_CSV)
    except Exception:
        return pd.DataFrame(columns=["name", "email", "category", "file", "reviewed", "timestamp"])

def save_progress_row(name, email, category, file_path):
    df = get_progress()
    rel_path = str(file_path.relative_to(ROOT))
    ts = datetime.now().isoformat()
    mask = (df["name"] == name) & (df["email"] == email) & (df["file"] == rel_path)
    if mask.any():
        df.loc[mask, ["reviewed", "timestamp"]] = [True, ts]
    else:
        df.loc[len(df)] = [name, email, category, rel_path, True, ts]
    df.to_csv(REVIEW_PROGRESS_CSV, index=False)

def record_signature(name, email, role, category, reviewed_files):
    ts_utc = datetime.utcnow().isoformat() + "Z"
    ts_local = datetime.now().isoformat()
    row = {
        "timestamp_utc": ts_utc,
        "timestamp_local": ts_local,
        "name": name,
        "email": email,
        "role": role,
        "category": category,
        "reviewed_files": "|".join(reviewed_files),
    }
    df = pd.read_csv(SIGNATURE_CSV)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(SIGNATURE_CSV, index=False)
    return row

def save_last_user(name, email, role):
    pd.DataFrame([{"name": name, "email": email, "role": role}]).to_csv(LAST_USER_CSV, index=False)

def load_last_user():
    try:
        df = pd.read_csv(LAST_USER_CSV)
        if not df.empty:
            return df.iloc[0].to_dict()
    except Exception:
        pass
    return {"name": "", "email": "", "role": ""}

# -------------------------------------------------
# SIDEBAR: CONTINUE SESSION
st.sidebar.header("User Session")
last_user = load_last_user()

if last_user["name"]:
    if st.sidebar.button(f"▶ Continue as {last_user['name']} ({last_user['email']})"):
        st.session_state["user_name"] = last_user["name"]
        st.session_state["user_email"] = last_user["email"]
        st.session_state["user_role"] = last_user["role"]
        st.sidebar.success("Session restored!")

# -------------------------------------------------
# MAIN UI
st.markdown("Please review all documents in each tab, mark them as **Reviewed**, and sign when finished. Progress is saved automatically.")

tabs = st.tabs(list
