# app.py
import io, os, re, base64
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
from PIL import Image
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# ---------------------- Page Config ----------------------
st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------------------- Font Styling ----------------------
FONT_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")
FONT_MAP = {
    "Regular": "PingAR+LT-Regular.otf",
    "Light": "PingAR+LT-Light.otf",
    "Medium": "PingAR+LT-Medium.otf",
    "Bold": "PingAR+LT-Bold.otf",
    "Black": "PingAR+LT-Black.otf",
    "ExtraLight": "PingAR+LT-ExtraLight.otf",
    "Thin": "PingAR+LT-Thin.otf",
    "Heavy": "PingAR+LT-Heavy.otf",
    "Hairline": "PingAR+LT-Hairline.otf",
}

with st.sidebar:
    st.subheader("🎨 Font Settings")
    selected_font = st.selectbox("Choose PingAR weight", list(FONT_MAP.keys()), index=0)

font_path = os.path.join(FONT_FOLDER, FONT_MAP[selected_font])

if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode("utf-8")
    font_css = f"""
    <style>
    @font-face {{
        font-family: 'PingAR';
        src: url(data:font/otf;base64,{font_base64}) format('opentype');
    }}
    html, body, [class*="css"]  {{
        font-family: 'PingAR', sans-serif !important;
    }}
    </style>
    """
    st.markdown(font_css, unsafe_allow_html=True)

# ---------------------- Helpers ----------------------
def sanitize_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(
    version: str,
    first_name: str = "",
    last_name: str = "",
    organization: str = "",
    title: str = "",
    phone: str = "",
    mobile: str = "",
    email: str = "",
    website: str = "",
    notes: str = "",
) -> str:
    lines = []
    if version == "3.0":
        lines += ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization.strip(): lines.append(f"ORG:{organization}")
        if title.strip():         lines.append(f"TITLE:{title}")
        if phone.strip():         lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile.strip():        lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email.strip():         lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website.strip():       lines.append(f"URL:{website}")
        if notes.strip():         lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines += ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization.strip(): lines.append(f"ORG:{organization}")
        if title.strip():         lines.append(f"TITLE:{title}")
        if phone.strip():         lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile.strip():        lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email.strip():         lines.append(f"EMAIL:{email}")
        if website.strip():       lines.append(f"URL:{website}")
        if notes.strip():         lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard_str: str) -> bytes:
    return vcard_str.replace("\n", "\r\n").encode("utf-8")

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

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

# ---------------------- UI ----------------------
st.title("🔳 vCard & Multi-QR Generator")

# vCard form
st.header("vCard Info")
c1, c2 = st.columns(2)
with c1:
    first_name = st.text_input("First Name / الاسم الأول")
    phone      = st.text_input("Phone (Work) / هاتف العمل", value="8001249000")
    email      = st.text_input("Email / البريد الإلكتروني")
with c2:
    last_name  = st.text_input("Last Name / اسم العائلة")
    mobile     = st.text_input("Mobile / الجوال")
    website    = st.text_input("Website / الموقع", value="https://alraedah.sa")

organization = st.text_input("Organization / الشركة", value="Alraedah Finance")
title        = st.text_input("Title / المسمى الوظيفي")
notes        = st.text_area("Notes / ملاحظات (اختياري)", height=100)

version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)

# Build vCard
vcard = build_vcard(
    version=version,
    first_name=first_name,
    last_name=last_name,
    organization=organization,
    title=title,
    phone=phone,
    mobile=mobile,
    email=email,
    website=website,
    notes=notes,
)

# Download button
vcf_fname = f"{sanitize_filename(first_name+'_'+last_name)}.vcf"
st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard), file_name=vcf_fname, mime="text/vcard")

st.code(vcard, language="text")