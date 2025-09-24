# app.py
import io, re, zipfile, base64
from datetime import datetime
from urllib.parse import urlencode, quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard_core(version, first, last, org, title, phone, mobile, email, website, notes):
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
    # dots
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

def short_data_uri(b: bytes, mediatype: str, max_len=80_000):
    b64 = base64.b64encode(b).decode("ascii")
    uri = f"data:{mediatype};base64,{b64}"
    return uri if len(uri) <= max_len else None

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
.card {
    background-color: #FFF; padding: 1.5rem; margin-bottom: 1.5rem;
    border-radius: 12px; border: 1px solid #E0E0E0; box-shadow: none;
}
.qr-preview {
    display: flex; justify-content: center; padding: 1rem;
    background: #F5F5F5; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #E0E0E0;
}
.stDownloadButton button, .stButton button { border-radius: 8px !important; background-color: #3A3A3A !important; color: #FFF !important; font-weight: 500 !important; border: none !important;}
.stDownloadButton button:hover, .stButton button:hover { background-color: #1E1E1E !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# Landing Page
# =========================
qs = st.query_params
if qs.get("view", [""])[0] == "landing":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📇 Contact & Actions")

    name = qs.get("name", [""])[0]
    if name: st.subheader(name)

    vcf = qs.get("vcf", [""])[0]
    wa  = qs.get("wa", [""])[0]
    site= qs.get("site", [""])[0]
    mailto= qs.get("mailto", [""])[0]
    tel = qs.get("tel", [""])[0]
    audio= qs.get("audio", [""])[0]
    video= qs.get("video", [""])[0]
    pdf  = qs.get("pdf", [""])[0]

    cols = st.columns(2)
    with cols[0]:
        if vcf: st.link_button("💾 Save Contact", vcf, use_container_width=True)
        if site: st.link_button("🌐 Website", site, use_container_width=True)
        if mailto: st.link_button("✉️ Email", mailto, use_container_width=True)
    with cols[1]:
        if wa: st.link_button("💬 WhatsApp", wa, use_container_width=True)
        if tel: st.link_button("📞 Call", tel, use_container_width=True)

    if audio or video or pdf:
        st.divider()
        st.subheader("📂 Media")
        if audio:
            if audio.startswith("data:audio"):
                st.audio(audio)
            else:
                st.link_button("🎧 Play Audio", audio, use_container_width=True)
        if video:
            if "youtube.com" in video or "youtu.be" in video:
                st.video(video)
            else:
                st.link_button("▶ Watch Video", video, use_container_width=True)
        if pdf:
            if pdf.startswith("data:application/pdf"):
                st.download_button("⬇ Download PDF", data=base64.b64decode(pdf.split(",")[1]),
                                   file_name="document.pdf", mime="application/pdf")
            else:
                st.link_button("📄 Open PDF", pdf, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =========================
# Main App
# =========================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Multi-QR"])

# ----------------------
# Multi-QR with Media
# ----------------------
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Multi-QR with Media")

    first = st.text_input("First Name", key="mq_first")
    last  = st.text_input("Last Name", key="mq_last")
    org   = st.text_input("Organization", key="mq_org")
    title = st.text_input("Title", key="mq_title")
    phone = st.text_input("Phone", key="mq_phone")
    mobile= st.text_input("Mobile", key="mq_mobile")
    email = st.text_input("Email", key="mq_email")
    website= st.text_input("Website", key="mq_site")
    notes = st.text_area("Notes", key="mq_notes")

    wa_num = st.text_input("WhatsApp number (intl digits, no +)", key="mq_wa")
    mailto = st.text_input("Email To (mailto)", key="mq_mailto")
    tel    = st.text_input("Call number", key="mq_tel")

    # Media
    st.subheader("Media Options")
    audio_file = st.file_uploader("Upload Audio (MP3/WAV)", type=["mp3","wav"], key="mq_audio")
    audio_data = ""
    if audio_file:
        raw = audio_file.read()
        mt = "audio/mpeg" if audio_file.name.endswith(".mp3") else "audio/wav"
        maybe = short_data_uri(raw, mt)
        if maybe: audio_data = maybe

    video_url = st.text_input("Video URL (YouTube/Vimeo/MP4)", key="mq_video")
    pdf_file  = st.file_uploader("Upload PDF", type=["pdf"], key="mq_pdf")
    pdf_data = ""
    if pdf_file:
        raw = pdf_file.read()
        maybe = short_data_uri(raw, "application/pdf")
        if maybe: pdf_data = maybe

    # Build vCard
    vcard = build_vcard_core("3.0", first, last, org, title, phone, mobile, email, website, notes)
    vcard_b64 = base64.b64encode(vcard_bytes(vcard)).decode("ascii")
    vcf_uri = f"data:text/vcard;base64,{vcard_b64}"

    wa_url = f"https://wa.me/{wa_num}" if wa_num else ""
    mailto_url = f"mailto:{mailto}" if mailto else ""
    tel_url = f"tel:{tel}" if tel else ""

    base = st.text_input("Base URL (your app link)", value="", key="mq_base")
    params = {
        "view":"landing", "name":f"{first} {last}".strip(),
        "vcf":vcf_uri
    }
    if wa_url: params["wa"] = wa_url
    if website: params["site"] = website
    if mailto_url: params["mailto"] = mailto_url
    if tel_url: params["tel"] = tel_url
    if audio_data: params["audio"] = audio_data
    if video_url: params["video"] = video_url
    if pdf_data: params["pdf"] = pdf_data

    landing_url = (base.rstrip("/") + "?" + urlencode(params, quote_via=quote_plus)) if base else "?" + urlencode(params, quote_via=quote_plus)
    st.text_input("Landing URL", value=landing_url, key="mq_link")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=2, key="mq_ec")
    box= st.slider("Box Size", 4, 20, 10, key="mq_box")
    border= st.slider("Border", 2, 10, 4, key="mq_border")

    if st.button("Generate Multi-QR", key="mq_btn"):
        img = make_qr_image(landing_url, ec, box, border, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Multi-QR")
        st.download_button("⬇ Download Multi-QR PNG", data=buf.getvalue(),
                           file_name=f"{sanitize_filename(first+'_'+last)}_multiqr.png",
                           mime="image/png", key="mq_dl")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
