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

def build_vcard(first, last, org, title, phone, mobile, email, website, notes):
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

def vcard_bytes(vcard: str) -> bytes:
    return vcard.replace("\n", "\r\n").encode("utf-8")

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

def make_qr_image(data: str, ec_label: str, box_size: int, border: int,
                  as_svg: bool, fg_color="#000000", bg_color="#FFFFFF", style="square"):
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
# Tabs
# =========================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Safe Landing Pages"])

# ==============================================================
# SINGLE MODE
# ==============================================================
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    first = st.text_input("First Name", key="single_first")
    last = st.text_input("Last Name", key="single_last")
    phone = st.text_input("Phone", key="single_phone")
    mobile = st.text_input("Mobile", "+966", key="single_mobile")
    email = st.text_input("Email", key="single_email")
    website = st.text_input("Website", key="single_website")
    org   = st.text_input("Organization", key="single_org")
    title = st.text_input("Title", key="single_title")
    notes = st.text_area("Notes", key="single_notes")

    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="single_ec")
    box_size = st.slider("Box Size", 4, 20, 10, key="single_box")
    border   = st.slider("Border", 2, 10, 4, key="single_border")
    fg_color = st.color_picker("QR Foreground", "#000000", key="single_fg")
    bg_color = st.color_picker("QR Background", "#FFFFFF", key="single_bg")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="single_style")

    if st.button("Generate vCard & QR", key="single_btn"):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(f"{first}_{last}")

        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard", key="single_dl_vcf")

        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.image(png_buf.getvalue(), caption="QR Code")
        st.download_button("⬇️ Download QR PNG", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png", key="single_dl_png")

        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR SVG", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml", key="single_dl_svg")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# BATCH MODE
# ==============================================================
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Batch Mode (Excel Upload)")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
        return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="batch_template")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name for this batch (optional)", key="batch_parent")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="batch_upload")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="batch_ec")
        box_size = st.slider("Box Size", 4, 20, 10, key="batch_box")
        border   = st.slider("Border", 2, 10, 4, key="batch_border")
        fg_color = st.color_picker("QR Foreground", "#000000", key="batch_fg")
        bg_color = st.color_picker("QR Background", "#FFFFFF", key="batch_bg")
        style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="batch_style")

        if st.button("Generate Batch ZIP", key="batch_btn"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    vcard = build_vcard(
                        str(row.get("First Name", "")),
                        str(row.get("Last Name", "")),
                        str(row.get("Organization", "")),
                        str(row.get("Title", "")),
                        str(row.get("Phone", "")),
                        str(row.get("Mobile", "")),
                        str(row.get("Email", "")),
                        str(row.get("Website", "")),
                        str(row.get("Notes", "")),
                    )
                    fname = sanitize_filename(f"{row.get('First Name','')}_{row.get('Last Name','')}") or "contact"

                    zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcard_bytes(vcard))

                    img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                                        fg_color=fg_color, bg_color=bg_color, style=style)
                    img_buf = io.BytesIO(); img.save(img_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", img_buf.getvalue())

                    svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

            zip_buf.seek(0)
            st.download_button("⬇️ Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{batch_folder}.zip", mime="application/zip", key="batch_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# SAFE LANDING PAGES
# ==============================================================
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Safe Landing Pages (inside app)")

    page_type = st.selectbox("Choose Landing Page Type", ["Contact Card", "Mini Bio", "Link Hub"], key="landing_type")

    if page_type == "Contact Card":
        name = st.text_input("Name", key="landing_name")
        phone = st.text_input("Phone", key="landing_phone")
        wa = st.text_input("WhatsApp (digits only)", key="landing_wa")
        email = st.text_input("Email", key="landing_email")

        landing_html = f"<h2>{name}</h2><p>📞 {phone}</p><p>💬 {wa}</p><p>✉️ {email}</p>"
        qr = make_qr_image(landing_html, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Landing QR")

    elif page_type == "Mini Bio":
        bio = st.text_area("Your Mini Bio", key="landing_bio")
        landing_html = f"<h2>About Me</h2><p>{bio}</p>"
        qr = make_qr_image(landing_html, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Landing QR")

    elif page_type == "Link Hub":
        links = st.text_area("Enter links (one per line)", key="landing_links")
        landing_html = "<h2>My Links</h2>" + "".join([f"<p>🔗 <a href='{l}'>{l}</a></p>" for l in links.splitlines() if l.strip()])
        qr = make_qr_image(landing_html, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Landing QR")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
