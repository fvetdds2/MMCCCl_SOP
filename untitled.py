# app.py
import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from datetime import datetime
import os
import io

# Optional: for reading docx content if you want inline preview (pip install python-docx)
try:
    import docx
except Exception:
    docx = None

st.set_page_config(page_title="Lab Onboarding — Document Review & Sign", layout="wide")

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

# --- Helper functions ---
def list_files(folder: Path):
    if not folder.exists():
        return []
    # common doc types
    exts = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".xls"]
    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in exts]
    return files

def file_download_link(file_path: Path, label: str = None):
    label = label or file_path.name
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_path.name}">{label}</a>'
    return href

def embed_pdf(file_path: Path, height: int = 700):
    """Return HTML to embed a PDF file inside an iframe using base64."""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    html = f'''
    <iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}px" style="border: none;"></iframe>
    '''
    st.components.v1.html(html, height=height+10)

def preview_docx(file_path: Path, max_paragraphs=40):
    if docx is None:
        st.write("Preview unavailable (python-docx not installed). Use download button.")
        return
    doc = docx.Document(str(file_path))
    text = []
    for i, para in enumerate(doc.paragraphs):
        text.append(para.text)
        if i+1 >= max_paragraphs:
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

# --- UI ---
st.title("Lab Onboarding — Document Review & Signature")
st.markdown(
    """
    Welcome! Use the tabs below to preview and review required documents.
    After marking each file as **Reviewed** in a category, sign the acknowledgement.
    Your signature (name/email/role/timestamp + files reviewed) will be recorded.
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

        # Container for files list + individual checkboxes
        reviewed = {}
        for f in files:
            st.subheader(f.name)
            col1, col2 = st.columns([2, 1])
            with col1:
                if f.suffix.lower() == ".pdf":
                    embed_pdf(f, height=450)
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
                st.markdown(file_download_link(f, label="Download file"), unsafe_allow_html=True)
            with col2:
                # Unique key per file so Streamlit remembers state
                checkbox_key = f"reviewed_{category_name}_{f.name}"
                reviewed[f.name] = st.checkbox("Reviewed", key=checkbox_key)

        st.markdown("---")
        st.write("When all files above are marked **Reviewed**, please sign below to record your acknowledgement.")

        all_reviewed = all(reviewed.values())
        if not all_reviewed:
            st.warning("You must mark every file above as Reviewed before signing.")
        # Signature form
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
                    st.write("A record of your acknowledgement has been saved. The onboarding admin will be notified (if configured).")

# --- Admin / download area ---
st.sidebar.header("Admin / Personal Log")
st.sidebar.write("Download the review/signature log or view recent signers.")

sign_df = get_signatures_df()
st.sidebar.download_button(
    label="Download signature log (CSV)",
    data=sign_df.to_csv(index=False).encode("utf-8"),
    file_name="review_signatures.csv",
    mime="text/csv",
)

st.sidebar.write("Recent signers:")
if sign_df.empty:
    st.sidebar.write("*No signatures recorded yet.*")
else:
    st.sidebar.table(sign_df.sort_values("timestamp_local", ascending=False).head(10))

# Optional: allow admin to upload missing docs
st.sidebar.markdown("---")
st.sidebar.header("Admin: Upload documents")
if st.sidebar.checkbox("Show upload form"):
    upload_cat = st.sidebar.selectbox("Category", list(CATEGORIES.keys()))
    uploaded = st.sidebar.file_uploader("Choose file to upload", accept_multiple_files=True)
    if st.sidebar.button("Upload"):
        target_dir = CATEGORIES[upload_cat]
        target_dir.mkdir(parents=True, exist_ok=True)
        for uf in uploaded:
            save_path = target_dir / uf.name
            with open(save_path, "wb") as f:
                f.write(uf.getbuffer())
        st.sidebar.success(f"Saved {len(uploaded)} file(s) to {target_dir}")

st.markdown("---")
st.caption("Developed by Data Science • Lab Onboarding Utility — modify folder paths as needed.")
