import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

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
    import base64
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

# Ensure folder structure exists
for folder in CATEGORIES.values():
    folder.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# DATA FILES
if not REVIEW_PROGRESS_CSV.exists():
    pd.DataFrame(columns=["name", "email", "category", "file", "reviewed", "timestamp"]).to_csv(REVIEW_PROGRESS_CSV, index=False)

if not SIGNATURE_CSV.exists():
    pd.DataFrame(columns=["timestamp_utc", "timestamp_local", "name", "email", "role", "category", "reviewed_files"]).to_csv(SIGNATURE_CSV, index=False)

# -------------------------------------------------
# HELPERS
def list_files(folder: Path):
    """List all PDF files, including subfolders."""
    return [p for p in sorted(folder.rglob("*.pdf")) if p.is_file()]

def get_progress():
    try:
        return pd.read_csv(REVIEW_PROGRESS_CSV)
    except Exception:
        return pd.DataFrame(columns=["name", "email", "category", "file", "reviewed", "timestamp"])

def save_progress_row(name, email, category, file_path):
    """Save progress when a file is reviewed."""
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

# -------------------------------------------------
# MAIN UI
st.markdown("Please review all documents in each tab, mark them as **Reviewed**, and sign when finished. Progress is saved automatically.")

tabs = st.tabs(list(CATEGORIES.keys()))
progress_df = get_progress()

for i, (category_name, folder) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        st.subheader(category_name)

        # List subfolders if any
        subfolders = sorted([p for p in folder.iterdir() if p.is_dir()])
        if not subfolders:
            subfolders = [folder]

        name = st.text_input(f"Your Name ({category_name})", key=f"name_{i}")
        email = st.text_input(f"Your Email ({category_name})", key=f"email_{i}")
        role = st.text_input(f"Your Role ({category_name})", key=f"role_{i}")

        if not name or not email:
            st.warning("Enter your name and email to track your review progress.")
            continue

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
                already_reviewed = (
                    (progress_df["name"] == name)
                    & (progress_df["email"] == email)
                    & (progress_df["file"] == rel_path)
                    & (progress_df["reviewed"] == True)
                )
                was_reviewed = already_reviewed.any()

                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(f"📄 {file_path.name}")
                with col2:
                    chk = st.checkbox(
                        "Reviewed",
                        value=was_reviewed,
                        key=f"chk_{category_name}_{file_path.name}",
                    )
                reviewed[file_path] = chk

                if chk and not was_reviewed:
                    save_progress_row(name, email, category_name, file_path)
                if chk:
                    reviewed_count += 1

                with open(file_path, "rb") as f:
                    st.download_button(
                        "📥 Download PDF",
                        data=f.read(),
                        file_name=file_path.name,
                        mime="application/pdf",
                        key=f"dl_{file_path.name}",
                    )

        st.progress(reviewed_count / max(total_files, 1))

        # --- Signature Section ---
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
                elif not name or not email:
                    st.error("Please fill in your name and email.")
                else:
                    reviewed_files = [p.name for p, val in reviewed.items() if val]
                    row = record_signature(name, email, role, category_name, reviewed_files)
                    st.success("Acknowledgement recorded ✅")
                    st.json(row)

# -------------------------------------------------
# SIDEBAR
st.sidebar.header("Admin / Personal Log")
sign_df = pd.read_csv(SIGNATURE_CSV)
if not sign_df.empty:
    st.sidebar.download_button(
        label="📥 Download Signature Log (CSV)",
        data=sign_df.to_csv(index=False).encode("utf-8"),
        file_name="review_signatures.csv",
        mime="text/csv",
    )
else:
    st.sidebar.write("*No signatures yet.*")

progress_df = get_progress()
if not progress_df.empty:
    st.sidebar.download_button(
        label="📥 Download Review Progress Log (CSV)",
        data=progress_df.to_csv(index=False).encode("utf-8"),
        file_name="review_progress.csv",
        mime="text/csv",
    )

st.sidebar.markdown("---")
st.sidebar.caption("Developed by Dollada Srisai")
