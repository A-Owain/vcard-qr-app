# app.py
import io, re, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="QR Generator Suite", page_icon="🔳", layout="centered")

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(first, last, org, title, phone, mobile, email, website, notes, version="3.0"):
    if version == "4.0":
        lines = ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{first} {last}".strip())
        if org: lines.append(f"ORG:{org}")
        if title: lines.append(f"TITLE:{title}")
        if phone: lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile: lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email: lines.append(f"EMAIL:{email}")
        if website: lines.append(f"URL:{website}")
        if notes: lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{first} {last}".strip())
        if org: lines.append(f"ORG:{org}")
        if title: lines.append(f"TITLE:{title}")
        if phone: lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile: lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email: lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website: lines.append(f"URL:{website}")
        if notes: lines.append(f"NOTE:{notes}")
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

def make_qr_image(data: str, ec_label: str, box_size: int, border: int, as_svg: bool,
                  fg_color="#000000", bg_color="#FFFFFF", style="square"):
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
    if style == "square":
        return qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGB")
    # dots style
    matrix = qr.get_matrix()
    rows, cols = len(matrix), len(matrix[0])
    size = (cols + border * 2) * box_size
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:
                x = (c + border) * box_size
                y = (r + border) * box_size
                draw.ellipse((x, y, x + box_size, y + box_size), fill=fg_color)
    return img

# =========================
# Translations
# =========================
t = {
    "English": {
        "title": "QR Generator Suite",
        "tabs": ["vCard Single", "Batch Mode", "WhatsApp", "Email", "Link", "Location"],
        "first": "First Name",
        "last": "Last Name",
        "org": "Organization",
        "job": "Title",
        "phone": "Phone",
        "mobile": "Mobile",
        "email": "Email",
        "website": "Website",
        "notes": "Notes",
        "generate": "Generate vCard & QR",
        "download_vcf": "Download vCard (.vcf)",
        "download_png": "Download QR PNG",
        "download_svg": "Download QR SVG",
        "batch_note": "Excel columns: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes",
    },
    "العربية": {
        "title": "مجموعة إنشاء رموز QR",
        "tabs": ["بطاقة فردية", "الوضع الجماعي", "واتساب", "البريد الإلكتروني", "رابط", "الموقع"],
        "first": "الاسم الأول",
        "last": "اسم العائلة",
        "org": "المؤسسة / الشركة",
        "job": "المسمى الوظيفي",
        "phone": "الهاتف",
        "mobile": "الجوال",
        "email": "البريد الإلكتروني",
        "website": "الموقع الإلكتروني",
        "notes": "ملاحظات",
        "generate": "إنشاء بطاقة و رمز QR",
        "download_vcf": "تحميل بطاقة (.vcf)",
        "download_png": "تحميل رمز QR (PNG)",
        "download_svg": "تحميل رمز QR (SVG)",
        "batch_note": "أعمدة الإكسل: الاسم الأول، اسم العائلة، الهاتف، الجوال، البريد الإلكتروني، الموقع الإلكتروني، المؤسسة، المسمى الوظيفي، ملاحظات",
    }
}

# =========================
# Language Switch
# =========================
lang = st.sidebar.radio("Language / اللغة", ["English", "العربية"], index=0)
labels = t[lang]

# =========================
# Styling
# =========================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'PingAR LT Regular', sans-serif;
    color: #222;
    background-color: #FAFAFA;
}
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1000px; }
.qr-preview {
    display: flex; justify-content: center; padding: 1rem;
    background: #F5F5F5; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #E0E0E0;
}
.stDownloadButton button, .stButton button {
    border-radius: 8px !important;
    background-color: #3A3A3A !important;
    color: #FFF !important;
    font-weight: 500 !important;
    border: none !important;
}
.stDownloadButton button:hover, .stButton button:hover {
    background-color: #1E1E1E !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Main App
# =========================
st.title(labels["title"])
tabs = st.tabs(labels["tabs"])

# --- vCard Single ---
with tabs[0]:
    st.header(labels["tabs"][0])
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    first = st.text_input(labels["first"])
    last  = st.text_input(labels["last"])
    org   = st.text_input(labels["org"])
    title = st.text_input(labels["job"])
    phone = st.text_input(labels["phone"])
    mobile= st.text_input(labels["mobile"])
    email = st.text_input(labels["email"])
    website= st.text_input(labels["website"])
    notes = st.text_area(labels["notes"])
    if st.button(labels["generate"]):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes, version)
        fname = sanitize_filename(f"{first}_{last}")
        st.download_button(labels["download_vcf"], data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard")
        img = make_qr_image(vcard, "M (15%)", 10, 4, as_svg=False)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.image(png_buf.getvalue(), caption="QR")
        st.download_button(labels["download_png"], data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png")
        svg_img = make_qr_image(vcard, "M (15%)", 10, 4, as_svg=True)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button(labels["download_svg"], data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml")

# --- Batch Mode ---
with tabs[1]:
    st.header(labels["tabs"][1])
    st.caption(labels["batch_note"])
    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
        return buf.getvalue()
    st.download_button("Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name (optional)")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str
    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())
        if st.button("Generate Batch ZIP"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last = str(row.get("Last Name", "")).strip()
                    fname = sanitize_filename(f"{first}_{last}") or "contact"
                    vcard = build_vcard(first, last,
                                        str(row.get("Organization", "")),
                                        str(row.get("Title", "")),
                                        str(row.get("Phone", "")),
                                        str(row.get("Mobile", "")),
                                        str(row.get("Email", "")),
                                        str(row.get("Website", "")),
                                        str(row.get("Notes", "")))
                    zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcard_bytes(vcard))
            zip_buf.seek(0)
            st.download_button(labels["download_zip"], data=zip_buf.getvalue(),
                               file_name=f"{batch_folder}.zip", mime="application/zip")

# --- WhatsApp ---
with tabs[2]:
    st.header(labels["tabs"][2])
    wa_num = st.text_input("WhatsApp Number (digits only, intl format)")
    wa_msg = st.text_input("Prefilled Message (optional)")
    if st.button("Generate WhatsApp QR"):
        wa_url = f"https://wa.me/{wa_num}"
        if wa_msg:
            wa_url += f"?text={quote_plus(wa_msg)}"
        img = make_qr_image(wa_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WhatsApp QR")

# --- Email ---
with tabs[3]:
    st.header(labels["tabs"][3])
    mail_to = st.text_input(labels["email"], key="email_to")
    mail_sub = st.text_input("Subject", key="email_sub")
    mail_body = st.text_area("Body", key="email_body")
    if st.button("Generate Email QR", key="email_btn"):
        params = []
        if mail_sub: params.append("subject=" + quote_plus(mail_sub))
        if mail_body: params.append("body=" + quote_plus(mail_body))
        mailto_url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
        img = make_qr_image(mailto_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Email QR")


# --- Link ---
with tabs[4]:
    st.header(labels["tabs"][4])
    link_url = st.text_input("Enter URL")
    if st.button("Generate Link QR"):
        if not link_url.startswith("http"):
            link_url = "https://" + link_url
        img = make_qr_image(link_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Link QR")

# --- Location ---
with tabs[5]:
    st.header(labels["tabs"][5])
    lat = st.text_input("Latitude")
    lon = st.text_input("Longitude")
    if st.button("Generate Location QR"):
        if lat and lon:
            loc_url = f"https://www.google.com/maps?q={lat},{lon}"
            img = make_qr_image(loc_url, "M (15%)", 10, 4, as_svg=False)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Location QR")

# =========================
# Footer
# =========================
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain | <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
