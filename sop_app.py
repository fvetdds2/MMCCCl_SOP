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

for folder in CATEGORIES.values():
    folder.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# INIT CSVs
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

def load_user_progress_to_state(name, email):
    df = get_progress()
    user_files = df[(df["name"] == name) & (df["email"] == email) & (df["reviewed"] == True)]["file"].tolist()
    st.session_state["reviewed_files"] = user_files

# -------------------------------------------------
# SIDEBAR SESSION RESTORE
st.sidebar.header("User Session")
last_user = load_last_user()

if st.sidebar.button(f"▶ Continue as {last_user['name']} ({last_user['email']})" if last_user["name"] else "No saved user"):
    st.session_state["restore_user"] = True
    st.experimental_rerun()

if st.session_state.get("restore_user", False):
    st.session_state["user_name"] = last_user["name"]
    st.session_state["user_email"] = last_user["email"]
    st.session_state["user_role"] = last_user["role"]
    load_user_progress_to_state(last_user["name"], last_user["email"])
    st.session_state["restore_user"] = False
    st.sidebar.success("Session restored! ✅")

# -------------------------------------------------
# MAIN UI
st.markdown("Please review all documents in each tab, mark them as **Reviewed**, and sign when finished. Progress is saved automatically.")
tabs = st.tabs(list(CATEGORIES.keys()))

for i, (category_name, folder) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        st.subheader(category_name)
        subfolders = sorted([p for p in folder.iterdir() if p.is_dir()])
        if not subfolders:
            subfolders = [folder]

        default_name = st.session_state.get("user_name", "")
        default_email = st.session_state.get("user_email", "")
        default_role = st.session_state.get("user_role", "")

        name = st.text_input(f"Your Name ({category_name})", value=default_name, key=f"name_{i}")
        email = st.text_input(f"Your Email ({category_name})", value=default_email, key=f"email_{i}")
        role = st.text_input(f"Your Role ({category_name})", value=default_role, key=f"role_{i}")

        if not name or not email:
            st.warning("Enter your name and email to track your review progress.")
            continue

        st.session_state["user_name"] = name
        st.session_state["user_email"] = email
        st.session_state["user_role"] = role
        save_last_user(name, email, role)

        if "reviewed_files" not in st.session_state:
            load_user_progress_to_state(name, email)
        reviewed_files = set(st.session_state.get("reviewed_files", []))

        reviewed = {}
        total_files = 0
        reviewed_count = 0

        for sub in subfolders:
            st.markdown(f"### 📁 {sub.name}")
            files = list_files(sub)
            if not files:
                st.info("No PDF files found in this folder.")
                continue

            for file_path in files:
                total_files += 1
                rel_path = str(file_path.relative_to(ROOT))
                was_reviewed = rel_path in reviewed_files

                col1, col2, col3 = st.columns([4, 1.5, 1])
                with col1:
                    st.write(f"📄 {file_path.name}")
                with col2:
                    with open(file_path, "rb") as f:
                        st.download_button(
                            "📥 Download PDF",
                            data=f.read(),
                            file_name=file_path.name,
                            mime="application/pdf",
                            key=f"dl_{category_name}_{file_path.name}",
                        )
                with col3:
                    chk = st.checkbox("Reviewed", value=was_reviewed, key=f"chk_{category_name}_{file_path.name}")

                reviewed[file_path] = chk
                if chk and not was_reviewed:
                    save_progress_row(name, email, category_name, file_path)
                    st.session_state["reviewed_files"].append(rel_path)
                if chk:
                    reviewed_count += 1

        st.progress(reviewed_count / max(total_files, 1))
        st.caption(f"{reviewed_count} of {total_files} documents reviewed.")

        st.markdown("---")
        st.write("When all files are marked **Reviewed**, please sign below.")

        all_reviewed = total_files > 0 and reviewed_count == total_files
        if not all_reviewed:
            st.info("You can stop and return later — progress is saved automatically.")

        with st.form(key=f"form_signature_{category_name}"):
            submit_btn = st.form_submit_button("Sign and Record Acknowledgement")
            if submit_btn:
                if not all_reviewed:
                    st.warning("Please review all files before final signing.")
                else:
                    reviewed_list = [p.name for p, val in reviewed.items() if val]
                    row = record_signature(name, email, role, category_name, reviewed_list)
                    st.success("Acknowledgement recorded ✅")
                    st.json(row)

# -------------------------------------------------
# SIDEBAR ADMIN
st.sidebar.markdown("---")
st.sidebar.header("Admin / Logs")

sign_df = pd.read_csv(SIGNATURE_CSV)
if not sign_df.empty:
    st.sidebar.download_button(
        label="📥 Download Signature Log (CSV)",
        data=sign_df.to_csv(index=False).encode("utf-8"),
        file_name="review_signatures.csv",
        mime="text/csv",
    )

progress_df = get_progress()
if not progress_df.empty:
    st.sidebar.download_button(
        label="📥 Download Review Progress Log (CSV)",
        data=progress_df.to_csv(index=False).encode("utf-8"),
        file_name="review_progress.csv",
        mime="text/csv",
    )

st.sidebar.caption("Developed by Dollada Srisai")
