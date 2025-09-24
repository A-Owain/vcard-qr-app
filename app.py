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

    img = qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGB")

    if style == "dots":
        img = qr_to_dots(img, fg_color, bg_color)

    if as_svg:
        return qr.make_image(image_factory=SvgImage)
    return img

def qr_to_dots(img: Image.Image, fg_color="black", bg_color="white") -> Image.Image:
    """Convert square QR modules into circular dots."""
    w, h = img.size
    module_size = w // img.width
    dot_img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(dot_img)

    pixels = img.load()
    for y in range(h):
        for x in range(w):
            if pixels[x, y] != (255, 255, 255):  # not white
                r = module_size // 2
                draw.ellipse(
                    (x, y, x + 1, y + 1),
                    fill=fg_color
                )
    return img

def try_make_qr(content: str, ec_label: str, box_size: int, border: int, as_svg: bool,
                fg_color="black", bg_color="white", style="square"):
    try:
        return make_qr_image(content, ec_label, box_size, border, as_svg, fg_color, bg_color, style), None
    except ValueError as e:
        if "Invalid version" in str(e):
            return None, "oversize"
        raise

def overlay_logo(pil_img: Image.Image, logo_bytes: bytes, scale: float = 0.22) -> Image.Image:
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    w = pil_img.size[0]
    target_w = max(20, int(w * float(scale)))
    aspect = logo.size[1] / logo.size[0]
    resized = logo.resize((target_w, int(target_w * aspect)), Image.LANCZOS)
    out = pil_img.convert("RGBA")
    x = (out.size[0] - resized.size[0]) // 2
    y = (out.size[1] - resized.size[1]) // 2
    out.alpha_composite(resized, (x, y))
    return out.convert("RGB")

# ---------- UI: Global settings ----------
st.title("🔳 vCard & Multi-QR Generator")
st.caption("Single or Batch Mode • Customizable QR Codes • PNG/SVG • Excel template")

with st.sidebar:
    st.header("QR Settings")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box_size = st.slider("Box Size", 4, 20, 10)
    border   = st.slider("Border", 2, 10, 4)
    fmt      = st.radio("QR Output Format", ["PNG", "SVG"], index=0)
    with_logo = st.checkbox("Add center logo (PNG/JPG)", value=False)
    logo_scale = st.slider("Logo relative size", 0.10, 0.35, 0.22, 0.01, disabled=not with_logo)
    logo_bytes = None
    if with_logo:
        logo_file = st.file_uploader("Upload logo", type=["png", "jpg", "jpeg"])
        if logo_file: logo_bytes = logo_file.read()

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
        pil = img.convert("RGB")
        if with_logo and logo_bytes:
            pil = overlay_logo(pil, logo_bytes, scale=logo_scale)
        b = io.BytesIO(); pil.save(b, format="PNG")
        st.image(b.getvalue())
        st.download_button("⬇️ Download QR", data=b.getvalue(), file_name=f"{base_name}_qr.png", mime="image/png")

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
                zf.writestr(f"{fname}/{fname}.vcf", vcf_bytes)

                # QR
                img = make_qr_image(vcard, ec_label, box_size, border, as_svg=(fmt=="SVG"),
                                    fg_color=fg_color, bg_color=bg_color, style=style)
                img_buf = io.BytesIO()
                if fmt == "SVG":
                    img.save(img_buf)
                    ext = "svg"
                else:
                    img = img.convert("RGB")
                    img.save(img_buf, format="PNG")
                    ext = "png"
                img_buf.seek(0)
                zf.writestr(f"{fname}/{fname}_qr.{ext}", img_buf.getvalue())
        zip_buf.seek(0)

        st.download_button(
            "⬇️ Download All Contacts (ZIP)",
            data=zip_buf,
            file_name="Batch_QR_vCards.zip",
            mime="application/zip"
        )
