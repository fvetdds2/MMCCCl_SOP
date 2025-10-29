import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import base64
import streamlit.components.v1 as components
from io import BytesIO

# -------------------------------------------------
# PAGE SETUP
# -------------------------------------------------
st.set_page_config(page_title="MMCCCL Onboarding Document Review & Sign", layout="wide")

# --- Custom Header Layout with logo on left and title on right ---
st.markdown("""
    <style>
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #f0f2f6;
        padding: 1rem 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: bold;
        color: #004080;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
logo_path = "mmcccl_logo.png"
if Path(logo_path).exists():
    logo_html = f'<img src="data:image/png;base64,{base64.b64encode(open(logo_path,"rb").read()).decode()}" width="120">'
else:
    logo_html = ""

st.markdown(f"""
    <div class="header-container">
        <div>{logo_html}</div>
        <div class="header-title">MMCCCL Onboarding Document Review & Sign</div>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
ROOT_DIR = Path("Onboarding_Documents")
ROOT_DIR.mkdir(exist_ok=True)

TEMP_DIR = Path(tempfile.gettempdir()) / "mmcccl_temp_pdfs"
TEMP_DIR.mkdir(exist_ok=True)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

@st.cache_data(show_spinner=False)
def list_files(folder: Path):
    """Return all supported files in directory."""
    exts = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".xls"]
    return [p for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in exts]


def embed_pdf(file_path: Path, height: int = 800):
    """Streamlit-friendly PDF preview that handles large files gracefully."""
    try:
        size_mb = file_path.stat().st_size / (1024 * 1024)
        temp_path = TEMP_DIR / file_path.name

        # Copy to temp folder for serving
        if not temp_path.exists():
            shutil.copy(file_path, temp_path)

        # Local file URL (prevents gray Chrome box)
        file_url = f"/media/{temp_path}"

        if size_mb < 5:  # Inline preview only for small files
            components.html(
                f"""
                <iframe
                    src="{file_url}#toolbar=1"
                    width="100%"
                    height="{height}px"
                    style="border:1px solid #ccc;border-radius:8px;"
                ></iframe>
                """,
                height=height + 20,
            )
        else:
            st.info(f"📄 {file_path.name} is large ({size_mb:.1f} MB). Open or download below.")
            st.markdown(f"[🔗 Open PDF in new tab]({file_url})", unsafe_allow_html=True)

        # Always include download button
        with open(file_path, "rb") as f:
            st.download_button(
                "📥 Download PDF",
                data=f.read(),
                file_name=file_path.name,
                mime="application/pdf",
            )

    except Exception as e:
        st.error(f"Could not preview {file_path.name}: {e}")


def read_docx(file_path: Path):
    """Safely extract text from docx."""
    from docx import Document
    try:
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"⚠️ Could not open {file_path.name}: {e}"


# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("📁 Document Folders")
subfolders = [f for f in ROOT_DIR.iterdir() if f.is_dir()]
selected_folder = st.sidebar.selectbox("Select a folder to view:", ["(Select)"] + [f.name for f in subfolders])

# -------------------------------------------------
# MAIN CONTENT
# -------------------------------------------------
if selected_folder != "(Select)":
    folder_path = ROOT_DIR / selected_folder
    st.markdown(f"### 📂 Folder: `{selected_folder}`")

    files = list_files(folder_path)

    if not files:
        st.warning("No supported files found in this folder.")
    else:
        for f in files:
            with st.expander(f"📄 {f.name}", expanded=False):
                suffix = f.suffix.lower()
                if suffix == ".pdf":
                    embed_pdf(f)
                elif suffix in [".docx", ".doc"]:
                    st.text_area("Document Preview", read_docx(f), height=400)
                    with open(f, "rb") as data:
                        st.download_button("📥 Download DOCX", data=data, file_name=f.name)
                elif suffix in [".xlsx", ".xls"]:
                    try:
                        df = pd.read_excel(f)
                        st.dataframe(df)
                        with open(f, "rb") as data:
                            st.download_button("📥 Download Excel", data=data, file_name=f.name)
                    except Exception as e:
                        st.error(f"Could not open Excel file: {e}")
                elif suffix == ".csv":
                    try:
                        df = pd.read_csv(f)
                        st.dataframe(df)
                        with open(f, "rb") as data:
                            st.download_button("📥 Download CSV", data=data, file_name=f.name)
                    except Exception as e:
                        st.error(f"Could not open CSV file: {e}")
                elif suffix == ".txt":
                    try:
                        st.text_area("Text File Content", f.read_text(), height=400)
                        with open(f, "rb") as data:
                            st.download_button("📥 Download TXT", data=data, file_name=f.name)
                    except Exception as e:
                        st.error(f"Could not open text file: {e}")
else:
    st.info("👈 Please select a folder from the sidebar to view its contents.")


# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
