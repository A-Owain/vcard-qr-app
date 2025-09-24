# app.py
import io, re, zipfile, base64
from datetime import datetime
from urllib.parse import quote_plus
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

def build_vcard(first_name, last_name, org, title, phone, mobile, email, website, notes):
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{first_name} {last_name}",
    ]
    if org:      lines.append(f"ORG:{org}")
    if title:    lines.append(f"TITLE:{title}")
    if phone:    lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
    if mobile:   lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
    if email:    lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
    if website:  lines.append(f"URL:{website}")
    if notes:    lines.append(f"NOTE:{notes}")
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
            if not val: continue
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
    font-family: 'Arial', sans-serif;
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
.stDownloadButton button, .stButton button {
    border-radius: 8px !important; background-color: #3A3A3A !important;
    color: #FFF !important; font-weight: 500 !important; border: none !important;
}
.stDownloadButton button:hover, .stButton button:hover { background-color: #1E1E1E !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# Main App Tabs
# =========================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single vCard", "Batch Mode", "Advanced QR"])

# ==============================================================
# SINGLE VCARD
# ==============================================================
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name")
        phone      = st.text_input("Phone (Work)")
        email      = st.text_input("Email")
        organization = st.text_input("Organization")
        website    = st.text_input("Website")
    with col2:
        last_name  = st.text_input("Last Name")
        mobile     = st.text_input("Mobile")
        title      = st.text_input("Title")
        notes      = st.text_area("Notes")

    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border   = st.slider("Border", 2, 10, 4)
    fg_color = st.color_picker("QR Foreground", "#000000")
    bg_color = st.color_picker("QR Background", "#FFFFFF")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0)

    if st.button("Generate vCard & QR"):
        vcard = build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(f"{first_name}_{last_name}")

        # vCard
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard")

        # PNG
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(buf.getvalue(), caption="vCard QR")
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download QR (PNG)", data=buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png")

        # SVG
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR (SVG)", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml")
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
        buf = io.BytesIO()
        df.to_excel(buf, index=False, sheet_name="Template")
        buf.seek(0)
        return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name for this batch (optional)")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box_size = st.slider("Box Size", 4, 20, 10, key="b_box")
        border   = st.slider("Border", 2, 10, 4, key="b_border")
        fg_color = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg_color = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="b_style")

        if st.button("Generate Batch ZIP"):
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
                    fname = sanitize_filename(str(row.get("First Name", "")) + "_" + str(row.get("Last Name", ""))) or "contact"

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
                               file_name=f"{batch_folder}.zip", mime="application/zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# ADVANCED QR (WiFi, Event, MeCard, Crypto, WhatsApp, Email)
# ==============================================================
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Advanced QR Codes")

    # WiFi
    st.subheader("📶 WiFi QR")
    ssid = st.text_input("SSID (Network Name)")
    password = st.text_input("Password")
    encryption = st.selectbox("Encryption", ["WPA", "WEP", "nopass"])
    if st.button("Generate WiFi QR"):
        wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
        img = make_qr_image(wifi_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WiFi QR")
        st.download_button("⬇️ WiFi QR", data=buf.getvalue(), file_name="wifi_qr.png", mime="image/png")

    # Event
    st.subheader("📅 Event QR")
    ev_title = st.text_input("Event Title")
    ev_start = st.text_input("Start (YYYYMMDDTHHMMSSZ)")
    ev_end   = st.text_input("End (YYYYMMDDTHHMMSSZ)")
    ev_loc   = st.text_input("Location")
    ev_desc  = st.text_area("Description")
    if st.button("Generate Event QR"):
        event_data = f"BEGIN:VEVENT\nSUMMARY:{ev_title}\nDTSTART:{ev_start}\nDTEND:{ev_end}\nLOCATION:{ev_loc}\nDESCRIPTION:{ev_desc}\nEND:VEVENT"
        img = make_qr_image(event_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Event QR")
        st.download_button("⬇️ Event QR", data=buf.getvalue(), file_name="event_qr.png", mime="image/png")

    # MeCard
    st.subheader("🪪 MeCard QR")
    mc_name  = st.text_input("Name (Last,First)")
    mc_phone = st.text_input("Phone")
    mc_email = st.text_input("Email")
    if st.button("Generate MeCard QR"):
        mecard = f"MECARD:N:{mc_name};TEL:{mc_phone};EMAIL:{mc_email};;"
        img = make_qr_image(mecard, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="MeCard QR")
        st.download_button("⬇️ MeCard QR", data=buf.getvalue(), file_name="mecard_qr.png", mime="image/png")

    # Crypto
    st.subheader("💰 Crypto QR")
    coin   = st.selectbox("Cryptocurrency", ["bitcoin", "ethereum"])
    wallet = st.text_input("Wallet Address")
    amount = st.text_input("Amount (optional)")
    if st.button("Generate Crypto QR"):
        crypto_data = f"{coin}:{wallet}"
        if amount: crypto_data += f"?amount={amount}"
        img = make_qr_image(crypto_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Crypto QR")
        st.download_button("⬇️ Crypto QR", data=buf.getvalue(), file_name="crypto_qr.png", mime="image/png")

    # WhatsApp
    st.subheader("💬 WhatsApp QR")
    wa_num = st.text_input("WhatsApp Number (intl digits, no +)")
    wa_msg = st.text_input("Prefilled Message (optional)")
    if st.button("Generate WhatsApp QR"):
        url = f"https://wa.me/{wa_num}"
        if wa_msg: url += f"?text={quote_plus(wa_msg)}"
        img = make_qr_image(url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WhatsApp QR")
        st.download_button("⬇️ WhatsApp QR", data=buf.getvalue(), file_name="whatsapp_qr.png", mime="image/png")

    # Email
    st.subheader("✉️ Email QR")
    mail_to = st.text_input("Recipient Email")
    mail_sub = st.text_input("Subject")
    mail_body = st.text_area("Body")
    if st.button("Generate Email QR"):
        params = []
        if mail_sub: params.append("subject=" + quote_plus(mail_sub))
        if mail_body: params.append("body=" + quote_plus(mail_body))
        url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
        img = make_qr_image(url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Email QR")
        st.download_button("⬇️ Email QR", data=buf.getvalue(), file_name="email_qr.png", mime="image/png")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
