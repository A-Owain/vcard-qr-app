# app.py
import io, os, re, base64, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
from PIL import Image
import pandas as pd
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Helpers ----------
def sanitize_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(version, first_name="", last_name="", organization="", title="", phone="", mobile="", email="", website="", notes="") -> str:
    """Return a vCard 3.0/4.0 without address/timezone."""
    lines = []
    if version == "3.0":
        lines += ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization: lines.append(f"ORG:{organization}")
        if title:        lines.append(f"TITLE:{title}")
        if phone:        lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile:       lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email:        lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website:      lines.append(f"URL:{website}")
        if notes:        lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines += ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization: lines.append(f"ORG:{organization}")
        if title:        lines.append(f"TITLE:{title}")
        if phone:        lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile:       lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email:        lines.append(f"EMAIL:{email}")
        if website:      lines.append(f"URL:{website}")
        if notes:        lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard_str: str) -> bytes:
    return vcard_str.replace("\n", "\r\n").encode("utf-8")

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

def make_qr_image(data: str, ec_label: str, box_size: int, border: int, as_svg: bool):
    qr = qrcode.QRCode(
        version=None,
        error_correction=EC_LEVELS[ec_label],
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    if as_svg:
        return qr.make_image(image_factory=SvgImage)
    return qr.make_image(fill_color="black", back_color="white")

# ---------- UI: Global settings ----------
st.title("🔳 vCard & Multi-QR Generator")
st.caption("Single vCard or Batch Mode with Excel upload")

with st.sidebar:
    st.header("QR Settings")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border   = st.slider("Border", 2, 10, 4)
    fmt      = st.radio("QR Output Format", ["PNG", "SVG"], index=0)

# ---------- Batch Mode ----------
st.header("📂 Batch Mode")

# Download template
def generate_excel_template():
    df = pd.DataFrame([
        {
            "First Name": "Abdurrahman",
            "Last Name": "Ali",
            "Organization": "Alraedah Finance",
            "Title": "Manager",
            "Phone": "8001249000",
            "Mobile": "966500000000",
            "Email": "abdurrahman@alraedah.sa",
            "Website": "https://alraedah.sa",
            "Notes": "VIP Contact"
        },
        {
            "First Name": "Sarah",
            "Last Name": "Mohammed",
            "Organization": "Elle Arabia",
            "Title": "Designer",
            "Phone": "8001234567",
            "Mobile": "966511111111",
            "Email": "sarah@elle.com",
            "Website": "https://elle.com",
            "Notes": "Cover Star"
        }
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="Template")
    buf.seek(0)
    return buf

st.download_button(
    "⬇️ Download Excel Template",
    data=generate_excel_template(),
    file_name="Batch_Template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

uploaded = st.file_uploader("📤 Upload Filled Excel (xlsx or csv)", type=["xlsx", "csv"])

if uploaded:
    # Read file
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    if st.button("⚙️ Generate Batch ZIP"):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                fname = sanitize_filename(f"{row['First Name']}_{row['Last Name']}")
                vcard = build_vcard(
                    version=version,
                    first_name=row.get("First Name", ""),
                    last_name=row.get("Last Name", ""),
                    organization=row.get("Organization", ""),
                    title=row.get("Title", ""),
                    phone=str(row.get("Phone", "")),
                    mobile=str(row.get("Mobile", "")),
                    email=row.get("Email", ""),
                    website=row.get("Website", ""),
                    notes=row.get("Notes", ""),
                )
                vcf_bytes = vcard_bytes(vcard)
                zf.writestr(f"{fname}/{fname}.vcf", vcf_bytes)

                # QR
                img = make_qr_image(vcard, ec_label, box_size, border, as_svg=(fmt=="SVG"))
                img_buf = io.BytesIO()
                if fmt == "SVG":
                    img.save(img_buf)
                    ext, mime = "svg", "image/svg+xml"
                else:
                    img = img.convert("RGB")
                    img.save(img_buf, format="PNG")
                    ext, mime = "png", "image/png"
                img_buf.seek(0)
                zf.writestr(f"{fname}/{fname}_qr.{ext}", img_buf.getvalue())
        zip_buf.seek(0)

        st.download_button(
            "⬇️ Download All Contacts (ZIP)",
            data=zip_buf,
            file_name="Batch_QR_vCards.zip",
            mime="application/zip"
        )
