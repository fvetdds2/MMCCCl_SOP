import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from datetime import datetime
import os

# -------------------------------------------------
# PAGE SETUP
st.set_page_config(page_title="MMCCCL Onboarding Document Review & Sign", layout="wide")

# --- Custom Header Layout with logo on left and title on right ---
from base64 import b64encode

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
        text-align: right; /* title now aligns right */
    }
    .logo-left {
        width: 400px;  /* adjust logo size */
        max-height: 200px;
        object-fit: contain;
    }
    </style>
""", unsafe_allow_html=True)

logo_path = "mmcccl_logo.png"
try:
    with open(logo_path, "rb") as f:
        logo_base64 = b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo-left" />'
except FileNotFoundError:
    logo_html = ""

st.markdown(
    f"""
    <div class="header-container">
        <div>{logo_html}</div>
        <div>
            <h1 class="main-header">MMCCCL Onboarding Document Review & Sign</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Optional: for reading docx content (install python-docx)
try:
    import docx
except Exception:
    docx = None

# --- CONFIG ---
ROOT = Path("docs")
CATEGORIES = {
    "Standard SOPs": ROOT / "sop",
    "Technical Documents": ROOT / "technical",
    "Safety Policies": ROOT / "safety",
}
SIGNATURES_DIR = Path("signatures")
SIGNATURES_DIR.mkdir(exist_ok=True)
SIGNATURE_CSV = SIGNATURES_DIR / "review_signatures.csv"

# ensure signature CSV exists with headers
if not SIGNATURE_CSV.exists():
    pd.DataFrame(columns=[
        "timestamp_utc", "timestamp_local", "name", "email", "role",
        "category", "reviewed_files"
    ]).to_csv(SIGNATURE_CSV, index=False)

# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------
def list_files(folder: Path):
    """List all supported files, including in subfolders."""
    if not folder.exists():
        return []
    exts = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".xls"]
    files = [p for p in sorted(folder.rglob("*")) if p.suffix.lower() in exts]
    return files

def embed_pdf(file_path: Path, height: int = 800):
    """Embed PDF directly inside Streamlit (Chrome-safe)."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        pdf_display = f"""
        <iframe
            src="data:application/pdf;base64,{b64}"
            width="100%"
            height="{height}px"
            style="border:1px solid #ddd; border-radius:10px;"
        ></iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not open {file_path.name}: {e}")

def file_download_link(file_path: Path, label: str = None):
    label = label or file_path.name
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_path.name}">{label}</a>'
    return href

def preview_docx(file_path: Path, max_paragraphs=40):
    if docx is None:
        st.write("Preview unavailable (python-docx not installed). Use download button.")
        return
    doc = docx.Document(str(file_path))
    text = []
    for i, para in enumerate(doc.paragraphs):
        text.append(para.text)
        if i + 1 >= max_paragraphs:
            break
    st.markdown("\n\n".join(text) if text else "*No preview text available.*")

def preview_excel(file_path: Path, nrows=50):
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        st.dataframe(df.head(nrows))
    except Exception as e:
        st.error(f"Couldn't preview Excel file: {e}")

def preview_text(file_path: Path, nlines=200):
    with open(file_path, "r", errors="ignore") as f:
        text = f.read()
    st.code(text[:20000])  # limit size

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
    return pd.read_csv(SIGNATURE_CSV)

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------
st.markdown(
    """
    Please review all documents in each tab, mark them as **Reviewed**, and sign when done.  
    """
)

tabs = st.tabs(list(CATEGORIES.keys()))

for i, (category_name, folder) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        st.header(category_name)
        st.write(f"Folder: `{folder}`")

        files = list_files(folder)
        if not files:
            st.info("No files found in this folder. Please ask the lab admin to upload required documents.")
            continue

        reviewed = {}
        for f in files:
            st.subheader(f.name)
            col1, col2 = st.columns([2, 1])
            with col1:
                if f.suffix.lower() == ".pdf":
                    st.write("PDF Preview:")
                    embed_pdf(f, height=600)
                elif f.suffix.lower() in [".doc", ".docx"]:
                    st.write("Preview (first paragraphs):")
                    preview_docx(f)
                elif f.suffix.lower() in [".xls", ".xlsx", ".csv"]:
                    st.write("Preview of the spreadsheet (first rows):")
                    preview_excel(f)
                elif f.suffix.lower() == ".txt":
                    preview_text(f)
                else:
                    st.write("No inline preview available.")
                st.markdown(file_download_link(f, label="📥 Download file"), unsafe_allow_html=True)
            with col2:
                checkbox_key = f"reviewed_{category_name}_{f.name}"
                reviewed[f.name] = st.checkbox("Reviewed", key=checkbox_key)

        st.markdown("---")
        st.write("When all files above are marked **Reviewed**, please sign below to record your acknowledgement.")

        all_reviewed = all(reviewed.values())
        if not all_reviewed:
            st.warning("You must mark every file above as Reviewed before signing.")

        with st.form(key=f"form_signature_{category_name}"):
            st.write("**Acknowledgement / Signature**")
            name = st.text_input("Full name", key=f"name_{category_name}")
            email = st.text_input("Email", key=f"email_{category_name}")
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
                    st.write("Your acknowledgement has been saved successfully.")

# -------------------------------------------------
# SIDEBAR ADMIN AREA
# -------------------------------------------------
st.sidebar.header("Admin / Personal Log")
st.sidebar.write("Download the review/signature log or view recent signers.")

sign_df = get_signatures_df()
st.sidebar.download_button(
    label="📥 Download signature log (CSV)",
    data=sign_df.to_csv(index=False).encode("utf-8"),
    file_name="review_signatures.csv",
    mime="text/csv",
)

st.sidebar.write("Recent signers:")
if sign_df.empty:
    st.sidebar.write("*No signatures recorded yet.*")
else:
    st.sidebar.table(sign_df.sort_values("timestamp_local", ascending=False).head(10))

# --- Admin Upload ---
st.sidebar.markdown("---")
st.sidebar.header("Admin: Upload documents")
if st.sidebar.checkbox("Show upload form"):
    upload_cat = st.sidebar.selectbox("Category", list(CATEGORIES.keys()))
    uploaded = st.sidebar.file_uploader("Choose file(s) to upload", accept_multiple_files=True)
    if st.sidebar.button("Upload"):
        target_dir = CATEGORIES[upload_cat]
        target_dir.mkdir(parents=True, exist_ok=True)
        for uf in uploaded:
            save_path = target_dir / uf.name
            with open(save_path, "wb") as f:
                f.write(uf.getbuffer())
        st.sidebar.success(f"Saved {len(uploaded)} file(s) to {target_dir}")

st.markdown("---")
st.caption("Developed by D • MMCCCL Lab Onboarding Utility")
