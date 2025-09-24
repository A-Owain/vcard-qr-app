# app.py
import io, re, zipfile, base64, json
from datetime import datetime
from urllib.parse import urlencode, quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# Query params (must be after Streamlit import & set_page_config)
qs = st.experimental_get_query_params()

# =========================
# HELPERS
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard_core(version, en_first, en_last, org, en_title, phone, mobile, email, website, notes,
                     ar_first=None, ar_last=None, ar_title=None):
    if version == "4.0":
        lines = ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{en_last};{en_first};;;")
        lines.append(f"FN:{en_first} {en_last}".strip())
        if org: lines.append(f"ORG:{org}")
        if en_title: lines.append(f"TITLE:{en_title}")
        if phone: lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile: lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email: lines.append(f"EMAIL:{email}")
        if website: lines.append(f"URL:{website}")
        if (ar_first or ar_last):
            fn_ar = (" ".join([ar_first or "", ar_last or ""])).strip()
            if fn_ar: lines.append(f"FN;LANGUAGE=ar:{fn_ar}")
        if ar_title: lines.append(f"TITLE;LANGUAGE=ar:{ar_title}")
        if notes: lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{en_last};{en_first};;;")
        lines.append(f"FN:{en_first} {en_last}".strip())
        if org: lines.append(f"ORG:{org}")
        if en_title: lines.append(f"TITLE:{en_title}")
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

    # custom dots/rounded
    matrix = qr.get_matrix()
    rows, cols = len(matrix), len(matrix[0])
    size = (cols + border * 2) * box_size
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if not val: continue
            x = (c + border) * box_size
            y = (r + border) * box_size
            if style == "dots":
                draw.ellipse((x, y, x + box_size, y + box_size), fill=fg_color)
            elif style == "rounded":
                pad = max(1, box_size // 8)
                radius = max(2, box_size // 4)
                draw.rounded_rectangle((x+pad, y+pad, x+box_size-pad, y+box_size-pad),
                                       radius=radius, fill=fg_color)
    return img

# =========================
# LANDING PAGES (safe, hosted inside app)
# =========================
if qs.get("view", [""])[0] == "contact":
    st.title("📇 Contact Card")
    st.write("Save this contact or reach out instantly.")
    if "vcf" in qs:
        vcard_data = base64.b64decode(qs["vcf"][0]).decode("utf-8")
        st.download_button("💾 Save vCard", vcard_bytes(vcard_data), "contact.vcf", "text/vcard")
    if "wa" in qs: st.link_button("💬 WhatsApp", qs["wa"][0])
    if "tel" in qs: st.link_button("📞 Call", qs["tel"][0])
    if "site" in qs: st.link_button("🌐 Website", qs["site"][0])
    st.stop()

if qs.get("view", [""])[0] == "links":
    st.title("🔗 Link Hub")
    st.write("Quick links")
    links = json.loads(base64.b64decode(qs["links"][0]).decode("utf-8")) if "links" in qs else []
    for label, url in links:
        st.link_button(label, url, use_container_width=True)
    st.stop()

if qs.get("view", [""])[0] == "audio":
    st.title("🔊 Audio Greeting")
    st.write("Play audio + save contact")
    if "audio" in qs:
        st.audio(base64.b64decode(qs["audio"][0]))
    if "vcf" in qs:
        vcard_data = base64.b64decode(qs["vcf"][0]).decode("utf-8")
        st.download_button("💾 Save vCard", vcard_bytes(vcard_data), "contact.vcf", "text/vcard")
    st.stop()

# =========================
# MAIN APP
# =========================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Advanced QR", "Safe Landing Pages"])

# ------------------------------
# Sidebar
# ------------------------------
with st.sidebar:
    st.header("App Base URL")
    st.session_state.app_base_url = st.text_input("Base URL (needed for landing QR)",
                                                  value=st.session_state.get("app_base_url", ""))

# ==============================================================
# SINGLE MODE
# ==============================================================
with tabs[0]:
    st.header("Single vCard Generator")
    first = st.text_input("First Name")
    last = st.text_input("Last Name")
    phone = st.text_input("Phone")
    email = st.text_input("Email")
    org   = st.text_input("Organization")
    title = st.text_input("Title")

    if st.button("Generate vCard & QR"):
        vcard = build_vcard_core("3.0", first, last, org, title, phone, "", email, "", "")
        fname = sanitize_filename(f"{first}_{last}")
        st.download_button("💾 Download vCard", vcard_bytes(vcard), f"{fname}.vcf", "text/vcard")

        img = make_qr_image(vcard, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="QR Code")
        st.download_button("⬇️ Download PNG", buf.getvalue(), f"{fname}.png", "image/png")

# ==============================================================
# BATCH MODE
# ==============================================================
with tabs[1]:
    st.header("Batch Mode")
    st.caption("Upload Excel with: First Name, Last Name, Phone, Email, Organization, Title")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("Generate Batch"):
        df = pd.read_excel(file)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                vcard = build_vcard_core("3.0", row["First Name"], row["Last Name"],
                                         row["Organization"], row["Title"],
                                         row["Phone"], "", row["Email"], "", "")
                fname = sanitize_filename(f"{row['First Name']}_{row['Last Name']}")
                zf.writestr(f"{fname}/{fname}.vcf", vcard_bytes(vcard))
        zip_buf.seek(0)
        st.download_button("⬇️ Download ZIP", zip_buf.getvalue(), "batch.zip", "application/zip")

# ==============================================================
# ADVANCED QR
# ==============================================================
with tabs[2]:
    st.header("Advanced QR")
    st.write("📶 WiFi, 📅 Events, 🪪 MeCard, 💰 Crypto")
    # (similar to your old version — keep if needed)

# ==============================================================
# SAFE LANDING PAGES
# ==============================================================
with tabs[3]:
    st.header("Safe Landing Pages")
    st.write("Choose one type of landing page:")
    st.markdown("1. **Contact Card**\n2. **Link Hub**\n3. **Audio Greeting**")

    choice = st.selectbox("Landing Type", ["Contact", "Links", "Audio"])
    base = st.session_state.app_base_url.rstrip("/")
    if not base:
        st.info("⚠️ Please set Base URL in sidebar for shareable links")

    if choice == "Contact":
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        wa = st.text_input("WhatsApp (digits)")
        vcard = build_vcard_core("3.0", name, "", "", "", phone, "", "", "", "")
        vcf_b64 = base64.b64encode(vcard.encode()).decode()
        params = {"view": "contact", "vcf": vcf_b64, "tel": f"tel:{phone}", "wa": f"https://wa.me/{wa}"}
        url = base + "?" + urlencode(params, quote_via=quote_plus) if base else ""
        st.text_input("Landing URL", url)

    elif choice == "Links":
        links = [("Website", "https://example.com"), ("Twitter", "https://twitter.com")]
        links_b64 = base64.b64encode(json.dumps(links).encode()).decode()
        params = {"view": "links", "links": links_b64}
        url = base + "?" + urlencode(params, quote_via=quote_plus) if base else ""
        st.text_input("Landing URL", url)

    elif choice == "Audio":
        audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])
        if audio_file:
            raw = audio_file.read()
            b64 = base64.b64encode(raw).decode()
            params = {"view": "audio", "audio": b64}
            url = base + "?" + urlencode(params, quote_via=quote_plus) if base else ""
            st.text_input("Landing URL", url)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align:center; font-size:0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
