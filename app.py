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

def safe_name_keep_case(s: str) -> str:
    # Keep case, replace spaces with underscores, keep only safe characters
    s = (s or "").strip().replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    return s or "contact"

def build_vcard(first, last, org, title, phone, mobile, email, website, notes, version="3.0"):
    if version == "4.0":
        lines = ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{(first + ' ' + last).strip()}")
        if org: lines.append(f"ORG:{org}")
        if title: lines.append(f"TITLE:{title}")
        if phone: lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{str(phone).strip()}")
        if mobile: lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{str(mobile).strip()}")
        if email: lines.append(f"EMAIL:{email}")
        if website: lines.append(f"URL:{website}")
        if notes: lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{(first + ' ' + last).strip()}")
        if org: lines.append(f"ORG:{org}")
        if title: lines.append(f"TITLE:{title}")
        if phone: lines.append(f"TEL;TYPE=WORK,VOICE:{str(phone).strip()}")
        if mobile: lines.append(f"TEL;TYPE=CELL,VOICE:{str(mobile).strip()}")
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
        # SVG factory renders square modules; colors/styles not applied to SVG in this simple path
        return qr.make_image(image_factory=SvgImage)

    if style == "square":
        return qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGB")

    # Dots style (PNG only)
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
# Main App
# =========================
st.title("🔳 QR Generator Suite")

tabs = st.tabs(["vCard Single", "Batch Mode", "WhatsApp", "Email", "Link", "Location"])

# --- vCard Single ---
with tabs[0]:
    st.header("Single vCard Generator")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0, key="s_version")
    first = st.text_input("First Name", key="s_first")
    last  = st.text_input("Last Name", key="s_last")
    org   = st.text_input("Organization", key="s_org")
    title = st.text_input("Title", key="s_title")
    phone = st.text_input("Phone", key="s_phone")
    mobile= st.text_input("Mobile", key="s_mobile")
    email = st.text_input("Email", key="s_email")
    website= st.text_input("Website", key="s_website")
    notes = st.text_area("Notes", key="s_notes")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="s_ec")
    box= st.slider("Box Size", 4, 20, 10, key="s_box")
    border= st.slider("Border", 2, 10, 4, key="s_border")
    fg = st.color_picker("QR Foreground", "#000000", key="s_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="s_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="s_style")

    if st.button("Generate vCard & QR", key="s_generate"):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes, version)
        fname = sanitize_filename(f"{first}_{last}")
        # vCard
        st.download_button("Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard", key="s_vcf_dl")
        # PNG QR
        img = make_qr_image(vcard, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.image(png_buf.getvalue(), caption="QR Code")
        st.download_button("Download QR PNG", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png", key="s_png_dl")
        # SVG QR
        svg_img = make_qr_image(vcard, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("Download QR SVG", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml", key="s_svg_dl")

# --- Batch Mode ---
with tabs[1]:
    st.header("Batch Mode (Excel Upload)")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
        return buf.getvalue()

    st.download_button("Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="b_template_dl")

    today_str = datetime.now().strftime("%Y%m%d")
    root_label = st.text_input("Root folder name", value="Batch_QR_vCards", key="b_root_label")
    root_folder = f"{(root_label or 'Batch_QR_vCards')}_{today_str}"
    st.caption(f"ZIP will contain a top-level folder named: **{root_folder}**")

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="b_uploader")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())
        ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box = st.slider("Box Size", 4, 20, 10, key="b_box")
        border = st.slider("Border", 2, 10, 4, key="b_border")
        fg = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style = st.radio("QR Style", ["square", "dots"], index=0, key="b_style")

        if st.button("Generate Batch ZIP", key="b_generate"):
            processed, missing = 0, 0
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "") or "").strip()
                    last  = str(row.get("Last Name", "") or "").strip()
                    if not first and not last:
                        missing += 1
                        continue

                    name_stub = safe_name_keep_case(f"{first}_{last}".strip("_"))
                    vcard = build_vcard(
                        first, last,
                        str(row.get("Organization", "") or ""),
                        str(row.get("Title", "") or ""),
                        str(row.get("Phone", "") or ""),
                        str(row.get("Mobile", "") or ""),
                        str(row.get("Email", "") or ""),
                        str(row.get("Website", "") or ""),
                        str(row.get("Notes", "") or "")
                    )

                    # Save vcf
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.vcf", vcard_bytes(vcard))

                    # Save png
                    img = make_qr_image(vcard, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.png", png_buf.getvalue())

                    # Save svg
                    svg_img = make_qr_image(vcard, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.svg", svg_buf.getvalue())

                    processed += 1

            zip_buf.seek(0)
            st.download_button("Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{root_folder}.zip", mime="application/zip", key="b_zip_dl")
            st.success(f"Done. Contacts processed: {processed} • Missing name rows: {missing} • Files created: {processed*3}")

            with zipfile.ZipFile(zip_buf, "r") as zcheck:
                with st.expander("Preview ZIP file list"):
                    st.write(zcheck.namelist()[:50])

# --- WhatsApp ---
with tabs[2]:
    st.header("WhatsApp QR")
    wa_num = st.text_input("WhatsApp Number (digits only, intl format)", key="w_num")
    wa_msg = st.text_input("Prefilled Message (optional)", key="w_msg")
    if st.button("Generate WhatsApp QR", key="w_generate"):
        wa_url = f"https://wa.me/{wa_num}"
        if wa_msg:
            wa_url += f"?text={quote_plus(wa_msg)}"
        img = make_qr_image(wa_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WhatsApp QR")
        st.download_button("WhatsApp QR (PNG)", data=buf.getvalue(),
                           file_name="whatsapp_qr.png", mime="image/png", key="w_dl")

# --- Email ---
with tabs[3]:
    st.header("Email QR")
    mail_to = st.text_input("Recipient", key="e_to")
    mail_sub = st.text_input("Subject", key="e_sub")
    mail_body = st.text_area("Body", key="e_body")
    if st.button("Generate Email QR", key="e_generate"):
        params = []
        if mail_sub: params.append("subject=" + quote_plus(mail_sub))
        if mail_body: params.append("body=" + quote_plus(mail_body))
        mailto_url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
        img = make_qr_image(mailto_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Email QR")
        st.download_button("Email QR (PNG)", data=buf.getvalue(),
                           file_name="email_qr.png", mime="image/png", key="e_dl")

# --- Link ---
with tabs[4]:
    st.header("Link QR")
    link_url = st.text_input("Enter URL", key="l_url")
    if st.button("Generate Link QR", key="l_generate"):
        url = link_url.strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        if url:
            img = make_qr_image(url, "M (15%)", 10, 4, as_svg=False)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Link QR")
            st.download_button("Link QR (PNG)", data=buf.getvalue(),
                               file_name="link_qr.png", mime="image/png", key="l_dl")
        else:
            st.warning("Please enter a valid URL.")

# --- Location ---
with tabs[5]:
    st.header("Location QR")
    lat = st.text_input("Latitude", key="loc_lat")
    lon = st.text_input("Longitude", key="loc_lon")
    gmap_link = st.text_input("Google Maps Link (optional)", key="loc_link")
    if st.button("Generate Location QR", key="loc_generate"):
        loc_url = ""
        if gmap_link.strip():
            loc_url = gmap_link.strip()
        elif lat and lon:
            loc_url = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            st.warning("Please provide either latitude & longitude or a Google Maps link.")
        if loc_url:
            img = make_qr_image(loc_url, "M (15%)", 10, 4, as_svg=False)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Location QR")
            st.download_button("Location QR (PNG)", data=buf.getvalue(),
                               file_name="location_qr.png", mime="image/png", key="loc_dl")

# =========================
# Footer
# =========================
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain | <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
