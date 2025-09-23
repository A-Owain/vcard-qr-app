# app.py
import io, re, base64
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
from PIL import Image
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# ---------- Page Config ----------
st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Custom Styling with PingAR+LT ----------
st.markdown(
    """
    <style>
    /* Load PingAR+LT font family */
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Regular.otf') format('opentype');
        font-weight: normal;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Bold.otf') format('opentype');
        font-weight: bold;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Light.otf') format('opentype');
        font-weight: 300;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Medium.otf') format('opentype');
        font-weight: 500;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-ExtraLight.otf') format('opentype');
        font-weight: 200;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Thin.otf') format('opentype');
        font-weight: 100;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Hairline.otf') format('opentype');
        font-weight: 50;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Heavy.otf') format('opentype');
        font-weight: 800;
    }
    @font-face {
        font-family: 'PingAR';
        src: url('/static/fonts/PingAR+LT-Black.otf') format('opentype');
        font-weight: 900;
    }

    html, body, [class*="css"] {
        font-family: 'PingAR', sans-serif !important;
    }

    h1, h2, h3 {
        font-family: 'PingAR', sans-serif !important;
        text-align: center;
    }

    /* QR card styling */
    .qr-card {
        background: #1E1E1E;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Helpers ----------
def build_vcard(version: str, first_name: str = "", last_name: str = "",
    organization: str = "", title: str = "", phone: str = "", mobile: str = "",
    email: str = "", website: str = "", notes: str = "") -> str:

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
        if notes.strip():
            safe_notes = notes.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{safe_notes}")
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
        if notes.strip():
            safe_notes = notes.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{safe_notes}")
        lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard_str: str) -> bytes:
    return vcard_str.replace("\n", "\r\n").encode("utf-8")

def vcard_data_uri(vcard_str: str, name: str) -> str:
    b = vcard_bytes(vcard_str)
    b64 = base64.b64encode(b).decode("ascii")
    return f"data:text/vcard;charset=utf-8;name={name}.vcf;base64,{b64}"

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

def try_make_qr(content: str, ec_label: str, box_size: int, border: int, as_svg: bool):
    try:
        return make_qr_image(content, ec_label, box_size, border, as_svg), None
    except ValueError as e:
        if "Invalid version" in str(e):
            return None, "oversize"
        raise

# ---------- UI ----------
st.title("🔳 vCard & Multi-QR Generator")
st.caption("Generate vCard + WhatsApp + Website + Email + Phone + Text • PNG/SVG • Data URI links • PingAR font & styled QR cards")

with st.sidebar:
    st.header("QR Settings")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size (px per module)", 4, 20, 10)
    border   = st.slider("Border (modules)", 2, 10, 4)
    fmt      = st.radio("QR Output Format", ["PNG", "SVG"], index=0)

# ---------- vCard builder ----------
st.header("vCard")
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

# Build vCard
display_name = (first_name + " " + last_name).strip() or "contact"
base_name    = (first_name + "_" + last_name).strip("_") or "contact"
timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")

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

vcf_fname = f"{base_name}_vcard_{timestamp}.vcf"
absolute_vcf_url = vcard_data_uri(vcard, base_name)

st.subheader("vCard Preview")
st.code(vcard, language="text")
st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard), file_name=vcf_fname, mime="text/vcard")

# Copy-to-clipboard button
st.text_input("Shareable vCard Data URI link", value=absolute_vcf_url)
st.markdown(f'<input type="text" value="{absolute_vcf_url}" id="copyTarget" style="width:100%;">', unsafe_allow_html=True)
st.markdown('<button onclick="navigator.clipboard.writeText(document.getElementById(\'copyTarget\').value)">📋 Copy Link</button>', unsafe_allow_html=True)

# ---------- MULTI-QR ----------
st.header("Multi-QR Contents")
with st.expander("WhatsApp"):
    wa_num   = st.text_input("WhatsApp number (digits only, intl format)", placeholder="9665XXXXXXXX")
    wa_msg   = st.text_input("Prefilled message (optional)")
with st.expander("Website"):
    web_url  = st.text_input("Website URL", value="https://alraedah.sa")
with st.expander("Email (mailto:)"):
    mail_to  = st.text_input("To", placeholder="name@example.com")
    mail_sub = st.text_input("Subject")
    mail_body= st.text_area("Body", height=80)
with st.expander("Phone (tel:)"):
    tel_num  = st.text_input("Phone number", placeholder="+966XXXXXXXXX")
with st.expander("Plain Text"):
    txt_raw  = st.text_area("Text to encode", height=80)

# vCard QR choice
st.subheader("vCard QR Content")
qr_choice = st.radio("vCard QR should encode:", ["Raw vCard text", "Data URI link"], index=0)
force_link_if_big = st.checkbox("Auto-use Data URI if QR too dense", value=True)

# Assemble items
items = []
items.append({
    "label": f"vCard ({display_name or 'contact'})",
    "content": vcard if qr_choice == "Raw vCard text" else absolute_vcf_url,
    "filename_stub": f"{base_name}_vcard_{timestamp}"
})
if wa_num:
    url = f"https://wa.me/{wa_num}"
    if wa_msg:
        url += f"?text={quote_plus(wa_msg)}"
    items.append({"label": "WhatsApp", "content": url, "filename_stub": f"{base_name}_whatsapp_{timestamp}"})
if web_url:
    items.append({"label": "Website", "content": web_url, "filename_stub": f"{base_name}_website_{timestamp}"})
if mail_to:
    params = []
    if mail_sub: params.append("subject=" + quote_plus(mail_sub))
    if mail_body: params.append("body=" + quote_plus(mail_body))
    url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
    items.append({"label": "Email", "content": url, "filename_stub": f"{base_name}_email_{timestamp}"})
if tel_num:
    items.append({"label": "Phone", "content": f"tel:{tel_num}", "filename_stub": f"{base_name}_phone_{timestamp}"})
if txt_raw:
    items.append({"label": "Text", "content": txt_raw, "filename_stub": f"{base_name}_text_{timestamp}"})

# ---------- Render QR gallery ----------
st.subheader("QR Gallery")
if not items:
    st.info("Add at least one item above to generate QR codes.")
else:
    cols = st.columns(2)
    for idx, item in enumerate(items):
        label = item["label"]
        content = item["content"]
        stub = item["filename_stub"]

        img, err = try_make_qr(content, ec_label, box_size, border, as_svg=(fmt=="SVG"))
        if err == "oversize" and label.startswith("vCard") and force_link_if_big:
            st.warning("vCard QR too dense. Preview switched to Data URI link.")
            content = absolute_vcf_url
            img, _ = try_make_qr(content, ec_label, box_size, border, as_svg=(fmt=="SVG"))

        with cols[idx % 2]:
            st.markdown(f'<div class="qr-card"><strong>{label}</strong>', unsafe_allow_html=True)
            if fmt == "SVG":
                if img:
                    b = io.BytesIO(); img.save(b)
                    st.markdown(b.getvalue().decode("utf-8"), unsafe_allow_html=True)
                    st.download_button("⬇️ Download SVG", data=b.getvalue(), file_name=f"{stub}.svg", mime="image/svg+xml")
            else:
                if img:
                    pil = img.convert("RGB")
                    b = io.BytesIO(); pil.save(b, format="PNG")
                    st.image(b.getvalue())
                    st.download_button("⬇️ Download PNG", data=b.getvalue(), file_name=f"{stub}.png", mime="image/png")
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("Made with ❤️ by Abdurrahman Alowain.")