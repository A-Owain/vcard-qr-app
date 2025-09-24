# app.py
import io, re, base64, zipfile
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Custom Styling ----------
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

/* Cards */
.card {
    background-color: #FFFFFF;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 12px;
    border: 1px solid #E0E0E0;
    box-shadow: none; /* minimal look */
}

/* QR Preview */
.qr-preview {
    display: flex;
    justify-content: center;
    padding: 1rem;
    background: #F5F5F5;
    border-radius: 10px;
    margin-bottom: 1rem;
    border: 1px solid #E0E0E0;
}

/* Buttons */
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

# ---------- Helpers ----------
def sanitize_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes):
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{first_name} {last_name}",
    ]
    if organization: lines.append(f"ORG:{organization}")
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
                  fg_color="black", bg_color="white", style="square"):
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

    # ---- DOTS STYLE ----
    matrix = qr.get_matrix()
    rows, cols = len(matrix), len(matrix[0])
    img_size = (cols + border * 2) * box_size
    img = Image.new("RGB", (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)

    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:  # dark module
                x = (c + border) * box_size
                y = (r + border) * box_size
                draw.ellipse((x, y, x + box_size, y + box_size), fill=fg_color)
    return img

# ---------- UI ----------
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode"])

with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone (Work)", "8001249000")
    mobile = st.text_input("Mobile", "+966")
    email = st.text_input("Email")
    website = st.text_input("Website")
    organization = st.text_input("Organization", "Alraedah Finance")
    title = st.text_input("Title")
    notes = st.text_area("Notes")

    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border = st.slider("Border", 2, 10, 4)
    fg_color = st.color_picker("QR Foreground", "#000000")
    bg_color = st.color_picker("QR Background", "#FFFFFF")
    style = st.radio("QR Style", ["square", "dots"], index=0)

    if st.button("Generate vCard & QR"):
        vcard = build_vcard(first_name, last_name, organization, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(first_name + "_" + last_name) or "contact"

        # Download vCard
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard")

        # PNG QR
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(buf.getvalue(), caption="QR Code")
        st.markdown('</div>', unsafe_allow_html=True)

        st.download_button("⬇️ Download QR PNG", data=buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png")

        # SVG QR
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                fg_color=fg_color, bg_color=bg_color, style=style)
        svg_buf = io.BytesIO()
        svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR SVG", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Batch Mode (Excel Upload)")
    st.caption("Upload an Excel with columns: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, sheet_name="Template")
        buf.seek(0)
        return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name for this batch (optional)", value="")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="batch_ec")
        box_size = st.slider("Box Size", 4, 20, 10, key="batch_box")
        border = st.slider("Border", 2, 10, 4, key="batch_border")
        fg_color = st.color_picker("QR Foreground", "#000000", key="batch_fg")
        bg_color = st.color_picker("QR Background", "#FFFFFF", key="batch_bg")
        style = st.radio("QR Style", ["square", "dots"], index=0, key="batch_style")

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
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", img_buf.getvalue())

                    svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                            fg_color=fg_color, bg_color=bg_color, style=style)
                    svg_buf = io.BytesIO()
                    svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

            zip_buf.seek(0)
            st.download_button("⬇️ Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{batch_folder}.zip", mime="application/zip")

            st.success(f"✅ Batch completed!\n"
                       f"Contacts processed: {len(df)}\n"
                       f"Files per contact: 3 (VCF, PNG, SVG)\n"
                       f"Total files in ZIP: {len(df) * 3}")
    st.markdown('</div>', unsafe_allow_html=True)
# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:
#888888;">Developed by Abdulrrahman Alowain | <a href="https://x.com/a_owain" target="_blank">Follow Me</a></p>
""", unsafe_allow_html=True)