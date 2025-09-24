# app.py
import io, re, zipfile, json, os, base64
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Helpers ----------
CONTACTS_DIR = "contacts"
os.makedirs(CONTACTS_DIR, exist_ok=True)

def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes):
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{first_name} {last_name}".strip(),
    ]
    if organization: lines.append(f"ORG:{organization}")
    if title:        lines.append(f"TITLE:{title}")
    if phone:        lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
    if mobile:       lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
    if email:        lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
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

    # Custom dots/rounded
    matrix = qr.get_matrix()
    rows, cols = len(matrix), len(matrix[0])
    size = (cols + border * 2) * box_size
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if not val:
                continue
            x = (c + border) * box_size
            y = (r + border) * box_size
            if style == "dots":
                draw.ellipse((x, y, x + box_size, y + box_size), fill=fg_color)
            elif style == "rounded":
                pad = max(1, box_size // 8)
                radius = max(2, box_size // 4)
                draw.rounded_rectangle(
                    (x + pad, y + pad, x + box_size - pad, y + box_size - pad),
                    radius=radius, fill=fg_color
                )
    return img

def save_contact(contact_id, data: dict):
    with open(os.path.join(CONTACTS_DIR, f"{contact_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_contact(contact_id):
    fpath = os.path.join(CONTACTS_DIR, f"{contact_id}.json")
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ---------- Styling ----------
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'PingAR LT Regular', sans-serif;
    color: #222;
    background-color: #FAFAFA;
}
.block-container { max-width: 900px; }
.card {
    background-color: #FFF;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 12px;
    border: 1px solid #E0E0E0;
}
.qr-preview {
    display: flex;
    justify-content: center;
    padding: 1rem;
    background: #F5F5F5;
    border-radius: 10px;
    margin-bottom: 1rem;
    border: 1px solid #E0E0E0;
}
.stDownloadButton button, .stButton button {
    border-radius: 8px !important;
    background-color: #3A3A3A !important;
    color: #FFF !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Landing Page Mode ----------
params = st.experimental_get_query_params()
if "contact" in params:
    contact_id = params["contact"][0]
    contact = load_contact(contact_id)
    if not contact:
        st.error("❌ Contact not found")
    else:
        st.title(f"{contact['first_name']} {contact['last_name']}")
        st.subheader(contact.get("title", ""))
        st.text(contact.get("organization", ""))

        # Action buttons
        if contact.get("phone"):
            st.markdown(f"📞 [Call]({ 'tel:' + contact['phone'] })")
        if contact.get("mobile"):
            st.markdown(f"📱 [Mobile]({ 'tel:' + contact['mobile'] })")
        if contact.get("email"):
            st.markdown(f"📧 [Email]({ 'mailto:' + contact['email'] })")
        if contact.get("website"):
            st.markdown(f"🌐 [Website]({contact['website']})")
        if contact.get("whatsapp"):
            st.markdown(f"💬 [WhatsApp](https://wa.me/{contact['whatsapp']})")

        # Download vCard
        st.download_button("💳 Download vCard", data=vcard_bytes(contact["vcard"]),
                           file_name=f"{sanitize_filename(contact_id)}.vcf",
                           mime="text/vcard")
    st.stop()

# ==============================================================
# Normal App (Tabs)
# ==============================================================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Advanced QR"])

# ==============================================================
# SINGLE MODE
# ==============================================================
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", key="s_first")
        phone      = st.text_input("Phone (Work)", key="s_phone")
        email      = st.text_input("Email", key="s_email")
        organization = st.text_input("Organization", key="s_org")
    with col2:
        last_name  = st.text_input("Last Name", key="s_last")
        mobile     = st.text_input("Mobile", key="s_mobile")
        website    = st.text_input("Website", key="s_web")
        title      = st.text_input("Title", key="s_title")

    notes = st.text_area("Notes", key="s_notes")

    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="s_ec")
    box_size = st.slider("Box Size", 4, 20, 10, key="s_box")
    border   = st.slider("Border", 2, 10, 4, key="s_border")
    fg_color = st.color_picker("QR Foreground", "#000000", key="s_fg")
    bg_color = st.color_picker("QR Background", "#FFFFFF", key="s_bg")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="s_style")

    if st.button("Generate vCard & QR", key="s_btn"):
        vcard = build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes)
        contact_id = sanitize_filename(f"{first_name}_{last_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Save contact for landing page
        save_contact(contact_id, {
            "first_name": first_name,
            "last_name": last_name,
            "organization": organization,
            "title": title,
            "phone": phone,
            "mobile": mobile,
            "email": email,
            "website": website,
            "vcard": vcard,
        })

        # Landing page URL
        base_url = st.secrets.get("app_url", "http://localhost:8501")
        landing_url = f"{base_url}/?contact={contact_id}"

        # Make QR that points to landing page
        img = make_qr_image(landing_url, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Landing Page QR")

        st.download_button("⬇️ Download QR PNG", data=buf.getvalue(),
                           file_name=f"{contact_id}_qr.png", mime="image/png")
        st.text_input("Landing Page URL", value=landing_url)
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# TODO: Batch + Advanced sections (similar structure, can also save contacts with IDs)
# ==============================================================

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">Developed by Abdulrrahman Alowain</p>
""", unsafe_allow_html=True)
