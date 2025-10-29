import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil
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
        gap: 1rem;
    }
    .main-header {
        color: #0072b2;
        font-size: 2.4rem;
        font-weight: 300;
        margin: 0;
        line-height: 1.2;
        flex: 1;
        text-align: right;
    }
    .logo-left {
        width: 400px;
        max-height: 200px;
        object-fit: contain;
    }
    </style>
""", unsafe_allow_html=True)

# --- Logo ---
logo_path = "mmcccl_logo.png"
if Path(logo_path).exists():
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo-left" />'
else:
    logo_html = ""

st.markdown(
    f"""
    <div class="header-container">
        <div>{logo_html}</div>
        <div><h1 class="main-header">MMCCCL Onboarding Document Review & Sign</h1></div>
    </div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# FOLDER CONFIGURATION
ROOT = Path("docs")
CATEGORIES = {
    "Standard SOPs": ROOT / "sop",
    "Technical Documents": ROOT / "technical",
    "Safety Policies": ROOT / "safety",
}

# Technical subfolders
TECH_SUBFOLDERS = [
    "Alinity c SOP",
    "Alinity i SOP",
    "Manual Testing SOP",
    "Operation Manual"
]

# Ensure folders exist
ROOT.mkdir(parents=True, exist_ok=True)
for folder in CATEGORIES.values():
    folder.mkdir(parents=True, exist_ok=True)
for sub in TECH_SUBFOLDERS:
    (CATEGORIES["Technical Documents"] / sub).mkdir(parents=True, exist_ok=True)

# Signature and review tracking
SIGNATURES_DIR = Path("signatures")
SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)

SIGNATURE_CSV = SIGNATURES_DIR / "review_signatures.csv"
REVIEW_STATUS_CSV = SIGNATURES_DIR / "review_status.csv"

# Initialize CSVs if missing
if not SIGNATURE_CSV.exists():
    pd.DataFrame(columns=["timestamp_utc", "timestamp_local", "name", "email", "role", "category", "reviewed_files"]).to_csv(SIGNATURE_CSV, index=False)

if not REVIEW_STATUS_CSV.exists():
    pd.DataFrame(columns=["email", "category", "file_key", "reviewed"]).to_csv(REVIEW_STATUS_CSV, index=False)

# -------------------------------------------------
# HELPERS
def list_files(folder: Path):
    exts = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".xls"]
    return [p for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in exts]

def get_signatures_df():
    try:
        return pd.read_csv(SIGNATURE_CSV)
    except Exception:
        return pd.DataFrame(columns=["timestamp_utc", "timestamp_local", "name", "email", "role", "category", "reviewed_files"])

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

# --- Persistent review tracking ---
def load_review_status(email: str):
    """Return a dict of previously reviewed files for a given user."""
    if not email:
        return {}
    try:
        df = pd.read_csv(REVIEW_STATUS_CSV)
        df = df[df["email"] == email]
        return {f"{row.category}:{row.file_key}": bool(row.reviewed) for _, row in df.iterrows()}
    except Exception:
        return {}

def update_review_status(email: str, category: str, file_key: str, reviewed: bool):
    """Save review checkbox state persistently."""
    if not email:
        return
    df = pd.read_csv(REVIEW_STATUS_CSV)
    mask = (df["email"] == email) & (df["category"] == category) & (df["file_key"] == file_key)
    if mask.any():
        df.loc[mask, "reviewed"] = reviewed
    else:
        df = pd.concat(
            [df, pd.DataFrame([{"email": email, "category": category, "file_key": file_key, "reviewed": reviewed}])],
            ignore_index=True
        )
    df.to_csv(REVIEW_STATUS_CSV, index=False)

# -------------------------------------------------
# MAIN CONTENT
st.markdown("""Please review all documents in each tab, mark them as **Reviewed**, and sign when done.""")

tabs = st.tabs(list(CATEGORIES.keys()))

for i, (category_name, folder) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        st.header(category_name)

        # --- EMAIL for session memory ---
        email_session = st.session_state.get("current_email", "")
        st.text_input("Enter your email to track progress:", key=f"email_entry_{category_name}", value=email_session)
        if st.session_state.get(f"email_entry_{category_name}"):
            st.session_state["current_email"] = st.session_state[f"email_entry_{category_name}"]
        email_session = st.session_state.get("current_email", "")

        reviewed_memory = load_review_status(email_session)
        reviewed = {}

        # --- Technical Documents (with subfolders) ---
        if category_name == "Technical Documents":
            for sub in TECH_SUBFOLDERS:
                subfolder = folder / sub
                st.subheader(sub)
                pdfs = list_files(subfolder)
                if not pdfs:
                    st.info(f"No files found in {sub}.")
                    continue
                for f in pdfs:
                    file_key = f"{sub}/{f.name}"
                    prev = reviewed_memory.get(f"{category_name}:{file_key}", False)
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(f"- {f.name}")
                    with cols[1]:
                        checked = st.checkbox("Reviewed", key=f"rev_{category_name}_{file_key}", value=prev)
                        if checked != prev and email_session:
                            update_review_status(email_session, category_name, file_key, checked)
                        reviewed[file_key] = checked
                    with open(f, "rb") as fb:
                        st.download_button("📥 Download", data=fb.read(), file_name=f.name, mime="application/pdf", key=f"dl_{category_name}_{file_key}")

        else:
            # --- Regular Categories ---
            pdfs = list_files(folder)
            if not pdfs:
                st.info("No files found in this folder.")
                continue
            for f in pdfs:
                file_key = f.name
                prev = reviewed_memory.get(f"{category_name}:{file_key}", False)
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"- {f.name}")
                with cols[1]:
                    checked = st.checkbox("Reviewed", key=f"rev_{category_name}_{file_key}", value=prev)
                    if checked != prev and email_session:
                        update_review_status(email_session, category_name, file_key, checked)
                    reviewed[file_key] = checked
                with open(f, "rb") as fb:
                    st.download_button("📥 Download", data=fb.read(), file_name=f.name, mime="application/pdf", key=f"dl_{category_name}_{file_key}")

        # --- Signature Section ---
        st.markdown("---")
        all_reviewed = all(reviewed.values()) if reviewed else False
        if not all_reviewed:
            st.warning("You must mark every file as Reviewed before signing.")

        with st.form(key=f"form_sign_{category_name}"):
            st.write("**Acknowledgement / Signature**")
            name = st.text_input("Full name", key=f"name_{category_name}")
            email = st.text_input("Email", value=email_session, key=f"email_{category_name}")
            role = st.text_input("Role / Position", key=f"role_{category_name}")
            submit_btn = st.form_submit_button("Sign and Record Acknowledgement")

            if submit_btn:
                if not all_reviewed:
                    st.error("Cannot sign: not all documents are marked as reviewed.")
                elif not name or not email:
                    st.error("Please provide your name and email before signing.")
                else:
                    reviewed_files = [fn for fn, val in reviewed.items() if val]
                    row = record_signature(name, email, role, category_name, reviewed_files)
                    st.success("Acknowledgement recorded ✅")
                    st.json(row)

# -------------------------------------------------
# SIDEBAR: ADMIN AREA
st.sidebar.header("Admin / Personal Log")

sign_df = get_signatures_df()
st.sidebar.download_button(
    label="📥 Download Signature Log (CSV)",
    data=sign_df.to_csv(index=False).encode("utf-8"),
    file_name="review_signatures.csv",
    mime="text/csv",
)

if sign_df.empty:
    st.sidebar.write("*No signatures recorded yet.*")
else:
    st.sidebar.table(sign_df.sort_values("timestamp_local", ascending=False).head(10))

st.sidebar.markdown("---")
st.sidebar.header("Admin: Upload Documents")

if st.sidebar.checkbox("Show upload form"):
    upload_cat = st.sidebar.selectbox("Category", list(CATEGORIES.keys()))
    uploaded = st.sidebar.file_uploader("Choose file(s) to upload", accept_multiple_files=True)
    if st.sidebar.button("Upload"):
        target_dir = CATEGORIES[upload_cat]
        if upload_cat == "Technical Documents":
            subchoice = st.sidebar.selectbox("Select subfolder", TECH_SUBFOLDERS)
            target_dir = target_dir / subchoice
        for uf in uploaded:
            save_path = target_dir / uf.name
            with open(save_path, "wb") as f:
                f.write(uf.getbuffer())
        st.sidebar.success(f"Saved {len(uploaded)} file(s) to {target_dir}")

st.markdown("---")
st.caption("Developed by Dollada Srisai")
