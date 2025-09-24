# app.py
import io, re, zipfile
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Helpers ----------
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

# ---------- QR Rendering ----------
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

    # Manual rendering for custom shapes (PNG only)
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
                    radius=radius,
                    fill=fg_color
                )
    return img

# ---------- Styling ----------
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'PingAR LT Regular', sans-serif;
    color: #222222;
    background-color: #FAFAFA;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 900px;
}
.card {
    background-color: #FFFFFF;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 12px;
    border: 1px solid #E0E0E0;
    box-shadow: none;
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
    color: #FFFFFF !important;
    font-weight: 500 !important;
    border: none !important;
}
.stDownloadButton button:hover, .stButton button:hover {
    background-color: #1E1E1E !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- UI ----------
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode"])

# -------- Single Mode --------
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name")
        phone      = st.text_input("Phone (Work)", "8001249000")
        email      = st.text_input("Email")
        organization = st.text_input("Organization")
    with col2:
        last_name  = st.text_input("Last Name")
        mobile     = st.text_input("Mobile", "+966")
        website    = st.text_input("Website")
        title      = st.text_input("Title")

    notes = st.text_area("Notes")

    st.subheader("QR Settings")
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border   = st.slider("Border", 2, 10, 4)
    fg_color = st.color_picker("QR Foreground", "#000000")
    bg_color = st.color_picker("QR Background", "#FFFFFF")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0)

    if st.button("Generate vCard & QR", use_container_width=True):
        vcard = build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(f"{first_name}_{last_name}")

        # vCard download
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard", use_container_width=True)

        # PNG QR
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG")

        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(png_buf.getvalue(), caption="QR Code")
        st.markdown('</div>', unsafe_allow_html=True)

        st.download_button("⬇️ Download QR (PNG)", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png", use_container_width=True)

        # SVG QR
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                fg_color=fg_color, bg_color=bg_color, style=style)
        svg_buf = io.BytesIO()
        svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR (SVG)", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml", use_container_width=True)

        # --- Secondary Option: ZIP with all files + SUMMARY ---
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr(f"{fname}/{fname}.vcf", vcard_bytes(vcard))
            zf.writestr(f"{fname}/{fname}_qr.png", png_buf.getvalue())
            zf.writestr(f"{fname}/{fname}_qr.svg", svg_buf.getvalue())

            summary = [
                "Single Contact Export Summary",
                "-----------------------------",
                f"Contact: {first_name} {last_name}",
                f"Organization: {organization}",
                f"Title: {title}",
                f"Files: 3 (VCF, PNG, SVG)",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            zf.writestr(f"{fname}/SUMMARY.txt", "\n".join(summary))

        zip_buf.seek(0)
        st.download_button("📦 Download All (ZIP)", data=zip_buf.getvalue(),
                           file_name=f"{fname}_bundle.zip", mime="application/zip", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -------- Batch Mode --------
# (unchanged from your working version, with SUMMARY.txt included)