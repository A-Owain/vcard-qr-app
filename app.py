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
        phone      = st.text_input("Phone (Work)", "8001249000", key="s_phone")
        email      = st.text_input("Email", key="s_email")
        organization = st.text_input("Organization", key="s_org")
    with col2:
        last_name  = st.text_input("Last Name", key="s_last")
        mobile     = st.text_input("Mobile", "+966", key="s_mobile")
        website    = st.text_input("Website", key="s_web")
        title      = st.text_input("Title", key="s_title")

    notes = st.text_area("Notes", key="s_notes")

    st.subheader("QR Settings")
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="s_ec")
    box_size = st.slider("Box Size", 4, 20, 10, key="s_box")
    border   = st.slider("Border", 2, 10, 4, key="s_border")
    fg_color = st.color_picker("QR Foreground", "#000000", key="s_fg")
    bg_color = st.color_picker("QR Background", "#FFFFFF", key="s_bg")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="s_style")

    if st.button("Generate vCard & QR", use_container_width=True, key="s_generate"):
        vcard = build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(f"{first_name}_{last_name}")

        # vCard download
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard",
                           use_container_width=True, key="s_dl_vcf")

        # PNG QR
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG")

        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(png_buf.getvalue(), caption="QR Code")
        st.markdown('</div>', unsafe_allow_html=True)

        st.download_button("⬇️ Download QR (PNG)", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png",
                           use_container_width=True, key="s_dl_png")

        # SVG QR
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                fg_color=fg_color, bg_color=bg_color, style=style)
        svg_buf = io.BytesIO()
        svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR (SVG)", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml",
                           use_container_width=True, key="s_dl_svg")

        # ZIP + SUMMARY
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
                           file_name=f"{fname}_bundle.zip", mime="application/zip",
                           use_container_width=True, key="s_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# BATCH MODE
# ==============================================================
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Batch Mode (Excel Upload)")
    st.caption("Excel columns: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame([{
            "First Name": "Ali",
            "Last Name": "Saud",
            "Phone": "8001249000",
            "Mobile": "+966500000000",
            "Email": "ali@example.com",
            "Website": "https://example.com",
            "Organization": "Sales Dept",
            "Title": "Manager",
            "Notes": "VIP Client"
        }], columns=cols)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, sheet_name="Template")
        buf.seek(0)
        return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True, key="b_dl_template")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name for this batch (optional)", key="b_parent")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="b_upload")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        st.subheader("Batch QR Settings")
        ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box_size = st.slider("Box Size", 4, 20, 10, key="b_box")
        border   = st.slider("Border", 2, 10, 4, key="b_border")
        fg_color = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg_color = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="b_style")

        if st.button("Generate Batch ZIP", use_container_width=True, key="b_generate"):
            names = []
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    fname = sanitize_filename(f"{first}_{last}") or "contact"
                    names.append(f"{first} {last}".strip())

                    vcard = build_vcard(first, last,
                                        str(row.get("Organization", "")),
                                        str(row.get("Title", "")),
                                        str(row.get("Phone", "")),
                                        str(row.get("Mobile", "")),
                                        str(row.get("Email", "")),
                                        str(row.get("Website", "")),
                                        str(row.get("Notes", "")))

                    # .vcf
                    zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcard_bytes(vcard))

                    # PNG
                    img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                                        fg_color=fg_color, bg_color=bg_color, style=style)
                    png_buf = io.BytesIO()
                    img.save(png_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", png_buf.getvalue())

                    # SVG
                    svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                            fg_color=fg_color, bg_color=bg_color, style=style)
                    svg_buf = io.BytesIO()
                    svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

                # SUMMARY.txt
                summary = [
                    "Batch Export Summary",
                    "---------------------",
                    f"Batch Folder: {batch_folder}",
                    f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Contacts: {len(names)}",
                    f"Files/contact: 3 (VCF, PNG, SVG)",
                    f"Total files: {len(names) * 3}",
                    "", "Contacts:"
                ] + [f"- {n}" for n in names]
                zf.writestr(f"{batch_folder}/SUMMARY.txt", "\n".join(summary))

            zip_buf.seek(0)
            st.download_button("⬇️ Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{batch_folder}.zip", mime="application/zip",
                               use_container_width=True, key="b_dl_zip")

            st.success(f"✅ Batch completed! Contacts: {len(df)} | Files per contact: 3 | Total: {len(df) * 3}")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# ADVANCED QR
# ==============================================================
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Advanced QR Codes")

    # --- WiFi ---
    st.subheader("📶 WiFi QR")
    ssid = st.text_input("SSID (Network Name)", key="adv_wifi_ssid")
    password = st.text_input("Password", key="adv_wifi_pass")
    encryption = st.selectbox("Encryption", ["WPA", "WEP", "nopass"], index=0, key="adv_wifi_enc")
    if st.button("Generate WiFi QR", key="adv_wifi_btn"):
        wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
        fname = sanitize_filename(f"wifi_{ssid}")
        img = make_qr_image(wifi_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WiFi QR")
        st.download_button("⬇️ WiFi QR PNG", data=buf.getvalue(), file_name=f"{fname}.png", mime="image/png", key="adv_wifi_dl_png")

    # --- Event ---
    st.subheader("📅 Event QR")
    ev_title = st.text_input("Event Title", key="adv_ev_title")
    ev_start = st.text_input("Start (YYYYMMDDTHHMMSSZ)", value="20250925T130000Z", key="adv_ev_start")
    ev_end = st.text_input("End (YYYYMMDDTHHMMSSZ)", value="20250925T140000Z", key="adv_ev_end")
    ev_loc = st.text_input("Location", key="adv_ev_loc")
    ev_desc = st.text_area("Description", key="adv_ev_desc")
    if st.button("Generate Event QR", key="adv_ev_btn"):
        event_data = f"""BEGIN:VEVENT
SUMMARY:{ev_title}
DTSTART:{ev_start}
DTEND:{ev_end}
LOCATION:{ev_loc}
DESCRIPTION:{ev_desc}
END:VEVENT"""
        fname = sanitize_filename(f"event_{ev_title}")
        img = make_qr_image(event_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Event QR")
        st.download_button("⬇️ Event QR PNG", data=buf.getvalue(), file_name=f"{fname}.png", mime="image/png", key="adv_ev_dl_png")

    # --- MeCard ---
    st.subheader("🪪 MeCard QR")
    mc_name = st.text_input("Name (Last,First)", key="adv_mc_name")
    mc_phone = st.text_input("Phone", key="adv_mc_phone")
    mc_email = st.text_input("Email", key="adv_mc_email")
    if st.button("Generate MeCard QR", key="adv_mc_btn"):
        mecard = f"MECARD:N:{mc_name};TEL:{mc_phone};EMAIL:{mc_email};;"
        fname = sanitize_filename(f"mecard_{mc_name}")
        img = make_qr_image(mecard, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="MeCard QR")
        st.download_button("⬇️ MeCard QR PNG", data=buf.getvalue(), file_name=f"{fname}.png", mime="image/png", key="adv_mc_dl_png")

    # --- Crypto ---
    st.subheader("💰 Crypto Payment QR")
    coin = st.selectbox("Cryptocurrency", ["bitcoin", "ethereum"], index=0, key="adv_cr_coin")
    wallet = st.text_input("Wallet Address", key="adv_cr_wallet")
    amount = st.text_input("Amount (optional)", key="adv_cr_amount")
    if st.button("Generate Crypto QR", key="adv_cr_btn"):
        crypto_data = f"{coin}:{wallet}"
        if amount:
            crypto_data += f"?amount={amount}"
        fname = sanitize_filename(f"{coin}_{wallet[:6]}")
        img = make_qr_image(crypto_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Crypto QR")
        st.download_button("⬇️ Crypto QR PNG", data=buf.getvalue(), file_name=f"{fname}.png", mime="image/png", key="adv_cr_dl_png")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a></p>
""", unsafe_allow_html=True)
