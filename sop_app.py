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

# --- Logo Display ---
logo_path = "mmcccl_logo.png"
if Path(logo_path).exists():
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo-left" />'
else:
    logo_html = ""

st.markdown(f"""
    <div class="header-container">
        <div>{logo_html}</div>
        <div><h1 class="main-header">MMCCCL Onboarding Document Review & Sign</h1></div>
    </div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# PATH CONFIGURATION
ROOT = Path("docs")
CATEGORIES = {
    "Standard SOPs": ROOT / "sop",
    "Technical Documents": ROOT / "technical",
    "Safety Policies": ROOT / "safety",
}
SIGNATURES_DIR = Path("signatures")
SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)
SIGNATURE_CSV = SIGNATURES_DIR / "review_signatures.csv"
REVIEW_STATUS_CSV = SIGNATURES_DIR / "review_status.csv"

# Ensure base folders exist
ROOT.mkdir(parents=True, exist_ok=True)
for folder in CATEGORIES.values():
    folder.mkdir(parents=True, exist_ok=True)

# Initialize tracking files
if not SIGNATURE_CSV.exists():
    pd.DataFrame(columns=[
        "timestamp_utc", "timestamp_local", "name", "email", "role",
        "category", "reviewed_files"
    ]).to_csv(SIGNATURE_CSV, index=False)

if not REVIEW_STATUS_CSV.exists():
    pd.DataFrame(columns=["email", "category", "file_key", "reviewed"]).to_csv(REVIEW_STATUS_CSV, index=False)

# -------------------------------------------------
# HELPER FUNCTIONS
def list_files(folder: Path):
    """List all PDF files recursively."""
    return [p for p in sorted(folder.rglob("*.pdf")) if p.is_file()]

def load_review_status(email: str):
    if not email:
        return {}
    try:
        df = pd.read_csv(REVIEW_STATUS_CSV)
        df = df[df["email"] == email]
        return {f"{row.category}:{row.file_key}": bool(row.reviewed) for _, row in df.iterrows()}
    except Exception:
        return {}

def update_review_status(email: str, category: str, file_key: str, reviewed: bool):
    if not email:
        return
    df = pd.read_csv(REVIEW_STATUS_CSV)
    mask = (df["email"] == email) & (df["category"] == category) & (df["file_key"] == file_key)
    if mask.any():
        df.loc[mask, "reviewed"] = reviewed
    else:
        df = pd.concat([df, pd.DataFrame([{
            "email": email,
            "category": category,
            "file_key": file_key,
            "reviewed": reviewed
        }])], ignore_index=True)
    df.to_csv(REVIEW_STATUS_CSV, index=False)

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

def get_signatures_df():
    try:
        return pd.read_csv(SIGNATURE_CSV)
    except Exception:
        return pd.DataFrame(columns=[
            "timestamp_utc", "timestamp_local", "name",
            "email", "role", "category", "reviewed_files"
        ])

# -------------------------------------------------
# MAIN PAGE UI
st.markdown("Please review all documents in each tab, mark them as **Reviewed**, and sign when done.")

email_global = st.text_input("Enter your email to load/save progress", key="user_email")
if email_global:
    st.session_state["current_email"] = email_global

review_memory = load_review_status(email_global)
tabs = st.tabs(list(CATEGORIES.keys()))

# -------------------------------------------------
# CATEGORY LOOP
for i, (category_name, folder) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        st.header(category_name)

        total_files = 0
        reviewed_files = 0

        if category_name == "Technical Documents":
            subfolders = [f for f in folder.iterdir() if f.is_dir()]
            for sub in subfolders:
                st.subheader(sub.name)
                pdfs = list_files(sub)
                if not pdfs:
                    st.info(f"No PDF files in {sub.name}.")
                    continue

                sub_total = len(pdfs)
                sub_reviewed = 0

                for f in pdfs:
                    total_files += 1
                    file_key = f"{sub.name}/{f.name}"
                    prev = review_memory.get(f"{category_name}:{file_key}", False)
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(f"📄 **{f.name}**")
                    with cols[1]:
                        checked = st.checkbox("Reviewed", value=prev, key=f"chk_{category_name}_{file_key}")
                    if checked != prev and email_global:
                        update_review_status(email_global, category_name, file_key, checked)
                    if checked:
                        reviewed_files += 1
                        sub_reviewed += 1

                # Progress bar for each subfolder
                st.progress(sub_reviewed / sub_total if sub_total else 0)
                st.caption(f"{sub_reviewed}/{sub_total} documents reviewed")

        else:
            pdfs = list_files(folder)
            total_files = len(pdfs)
            if not pdfs:
                st.info("No PDF files found.")
                continue

            for f in pdfs:
                file_key = f.name
                prev = review_memory.get(f"{category_name}:{file_key}", False)
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"📄 **{f.name}**")
                with cols[1]:
                    checked = st.checkbox("Reviewed", value=prev, key=f"chk_{category_name}_{file_key}")
                if checked != prev and email_global:
                    update_review_status(email_global, category_name, file_key, checked)
                if checked:
                    reviewed_files += 1

        # Overall progress for category
        if total_files > 0:
            progress = reviewed_files / total_files
        else:
            progress = 0

        st.markdown("---")
        st.write(f"**Overall Progress for {category_name}:**")
        st.progress(progress)
        st.caption(f"✅ {reviewed_files}/{total_files} documents reviewed")

        # Signature section
        if progress < 1.0:
            st.warning("⚠️ You must review all documents before signing.")
        else:
            with st.form(key=f"form_signature_{category_name}"):
                st.write("**Acknowledgement / Signature**")
                name = st.text_input("Full Name", key=f"name_{category_name}")
                role = st.text_input("Role / Position", key=f"role_{category_name}")
                submit_btn = st.form_submit_button("Sign and Record Acknowledgement")
                if submit_btn:
                    reviewed_list = [
                        k.split(":", 1)[1]
                        for k, v in review_memory.items()
                        if v and k.startswith(category_name)
                    ]
                    record_signature(name, email_global, role, category_name, reviewed_list)
                    st.success("✅ Acknowledgement recorded successfully!")

# -------------------------------------------------
# SIDEBAR
st.sidebar.header("Admin / Logs")
sign_df = get_signatures_df()

if email_global:
    user_records = sign_df[sign_df["email"] == email_global]
    if not user_records.empty:
        st.sidebar.download_button(
            label="📥 Download Your Signed Records (CSV)",
            data=user_records.to_csv(index=False).encode("utf-8"),
            file_name=f"{email_global}_signed_records.csv",
            mime="text/csv",
        )

st.sidebar.markdown("---")
st.caption("Developed by Dollada Srisai")
