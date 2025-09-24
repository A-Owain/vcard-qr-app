# app.py
import io, os, re, base64, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
from PIL import Image, ImageDraw
import pandas as pd
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# ---------- Helpers ----------
def sanitize_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(version, first_name="", last_name="", organization="", title="", phone="", mobile="", email="", website="", notes="") -> str:
    lines = []
    if version == "3.0":
        lines += ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization: lines.append(f"ORG:{organization}")
        if title:        lines.append(f"TITLE:{title}")
        if phone:        lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile:       lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email:        lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website:      lines.append(f"URL:{website}")
        if notes:        lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines += ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization: lines.append(f"ORG:{organization}")
        if title:        lines.append(f"TITLE:{title}")
        if phone:        lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile:       lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email:        lines.append(f"EMAIL:{email}")
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

def try_make_qr(content: str, ec_label: str, box_size: int, border: int, as_svg: bool,
                fg_color="black", bg_color="white", style="square"):
    try:
        return make_qr_image(content, ec_label, box_size, border, as_svg, fg_color, bg_color, style), None
    except ValueError as e:
        if "Invalid version" in str(e):
            return None, "oversize"
        raise

# ---------- UI: Global settings ----------
st.title("🔳 vCard & Multi-QR Generator")
st.caption("Single or Batch Mode • vCard + QR • PNG & SVG • Custom Colors & Styles")

with st.sidebar:
    st.header("QR Settings")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border   = st.slider("Border", 2, 10, 4)
    fmt      = st.radio("QR Output Format", ["PNG", "SVG"], index=0)

    st.subheader("🎨 QR Customization")
    fg_color = st.color_picker("Foreground color", "#000000")
    bg_color = st.color_picker("Background color", "#FFFFFF")
    style = st.radio("QR Style", ["square", "dots"], index=0)

# ---------- Single vCard mode ----------
st.header("👤 Single Contact Mode")
c1, c2 = st.columns(2)
with c1:
    first_name = st.text_input("First Name")
    phone      = st.text_input("Phone (Work)", value="8001249000")
    email      = st.text_input("Email")
with c2:
    last_name  = st.text_input("Last Name")
    mobile     = st.text_input("Mobile")
    website    = st.text_input("Website", value="https://alraedah.sa")

organization = st.text_input("Organization", value="Alraedah Finance")
title        = st.text_input("Title")
notes        = st.text_area("Notes", height=100)

display_name = (first_name + " " + last_name).strip() or "contact"
base_name    = (first_name + "_" + last_name).strip("_") or "contact"
timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")

# Build vCard
vcard = build_vcard(version, first_name, last_name, organization, title, phone, mobile, email, website, notes)
vcf_fname = f"{base_name}_vcard_{timestamp}.vcf"

st.subheader("vCard Preview")
st.code(vcard, language="text")
st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard), file_name=vcf_fname, mime="text/vcard")

# QR
st.subheader("QR for this vCard")
img, _ = try_make_qr(vcard, ec_label, box_size, border, as_svg=(fmt=="SVG"),
                     fg_color=fg_color, bg_color=bg_color, style=style)
if img:
    if fmt == "SVG":
        b = io.BytesIO(); img.save(b)
        st.markdown(b.getvalue().decode("utf-8"), unsafe_allow_html=True)
    else:
        b = io.BytesIO(); img.save(b, format="PNG")
        st.image(b.getvalue())
        st.download_button("⬇️ Download QR (PNG)", data=b.getvalue(), file_name=f"{base_name}_qr.png", mime="image/png")

# ---------- Batch Mode ----------
st.header("📂 Batch Mode")

def generate_excel_template():
    df = pd.DataFrame([
        {
            "First Name": "Abdurrahman",
            "Last Name": "Ali",
            "Organization": "Alraedah Finance",
            "Title": "Manager",
            "Phone": "8001249000",
            "Mobile": "966500000000",
            "Email": "abdurrahman@alraedah.sa",
            "Website": "https://alraedah.sa",
            "Notes": "VIP Contact"
        },
        {
            "First Name": "Sarah",
            "Last Name": "Mohammed",
            "Organization": "Elle Arabia",
            "Title": "Designer",
            "Phone": "8001234567",
            "Mobile": "966511111111",
            "Email": "sarah@elle.com",
            "Website": "https://elle.com",
            "Notes": "Cover Star"
        }
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="Template")
    buf.seek(0)
    return buf

st.download_button(
    "⬇️ Download Excel Template",
    data=generate_excel_template(),
    file_name="Batch_Template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

uploaded = st.file_uploader("📤 Upload Filled Excel (xlsx or csv)", type=["xlsx", "csv"])

# 🔹 NEW FEATURE: parent folder for batch
batch_folder = st.text_input("Parent folder name for this batch (optional)", value="Batch_Contacts")

if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    if st.button("⚙️ Generate Batch ZIP"):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                fname = sanitize_filename(f"{row['First Name']}_{row['Last Name']}")
                vcard = build_vcard(
                    version=version,
                    first_name=row.get("First Name", ""),
                    last_name=row.get("Last Name", ""),
                    organization=row.get("Organization", ""),
                    title=row.get("Title", ""),
                    phone=str(row.get("Phone", "")),
                    mobile=str(row.get("Mobile", "")),
                    email=row.get("Email", ""),
                    website=row.get("Website", ""),
                    notes=row.get("Notes", ""),
                )
                vcf_bytes = vcard_bytes(vcard)
                zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcf_bytes)

                # QR PNG
                img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                                    fg_color=fg_color, bg_color=bg_color, style=style)
                img_buf = io.BytesIO()
                img.save(img_buf, format="PNG")
                img_buf.seek(0)
                zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", img_buf.getvalue())

                # QR SVG
                svg_buf = io.BytesIO()
                img_svg = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                        fg_color=fg_color, bg_color=bg_color, style=style)
                img_svg.save(svg_buf)
                svg_buf.seek(0)
                zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

        zip_buf.seek(0)

        st.download_button(
            "⬇️ Download All Contacts (ZIP)",
            data=zip_buf,
            file_name=f"{batch_folder}.zip",
            mime="application/zip"
        )
