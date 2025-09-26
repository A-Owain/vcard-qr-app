import io, re, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# Barcode safe import
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

st.set_page_config(page_title="QR & Barcode Suite", page_icon="🔳", layout="centered")

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(first, last, org, title, phone, mobile, email, website, notes, version="3.0"):
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
    # dots style
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

def zip_files(file_dict):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for fname, content in file_dict.items():
            zf.writestr(fname, content)
    zip_buf.seek(0)
    return zip_buf.getvalue()

def show_qr_result(data, fname, ec, box, border, fg, bg, style):
    files = {}
    # PNG
    img = make_qr_image(data, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
    files[f"{fname}.png"] = png_buf.getvalue()
    st.image(png_buf.getvalue(), caption="QR Code")
    st.download_button("⬇️ Download PNG", png_buf.getvalue(), f"{fname}.png", "image/png")

    # SVG
    svg_img = make_qr_image(data, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
    files[f"{fname}.svg"] = svg_buf.getvalue()
    st.download_button("⬇️ Download SVG", svg_buf.getvalue(), f"{fname}.svg", "image/svg+xml")

    # ZIP
    st.download_button("⬇️ Download All (ZIP)", zip_files(files), f"{fname}_qr.zip", "application/zip")

# =========================
# UI
# =========================
st.title("🔳 QR & Barcode Suite")

tabs = st.tabs(["vCard Single", "Batch Mode", "WhatsApp", "Email", "Link", "Location", "Barcode"])

# --- vCard Single ---
with tabs[0]:
    st.header("Single vCard Generator")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
    first = st.text_input("First Name")
    last  = st.text_input("Last Name")
    org   = st.text_input("Organization")
    title = st.text_input("Title")
    phone = st.text_input("Phone")
    mobile= st.text_input("Mobile")
    email = st.text_input("Email")
    website= st.text_input("Website")
    notes = st.text_area("Notes")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box= st.slider("Box Size", 4, 20, 10)
    border= st.slider("Border", 2, 10, 4)
    fg = st.color_picker("QR Foreground", "#000000")
    bg = st.color_picker("QR Background", "#FFFFFF")
    style = st.radio("QR Style", ["square", "dots"], index=0)

    if st.button("Generate vCard & QR"):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes, version)
        fname = sanitize_filename(f"{first}_{last}")
        files = {}
        # VCF
        vcf_bytes = vcard_bytes(vcard)
        files[f"{fname}.vcf"] = vcf_bytes
        st.download_button("⬇️ Download vCard (.vcf)", vcf_bytes, f"{fname}.vcf", mime="text/vcard")
        # QR
        show_qr_result(vcard, fname, ec, box, border, fg, bg, style)
        # Add vcf to ZIP
        st.download_button("⬇️ Download All (ZIP incl. VCF)", zip_files(files), f"{fname}_all.zip", "application/zip")

# --- Batch Mode ---
with tabs[1]:
    st.header("Batch Mode (Excel Upload)")
    st.info("Upload Excel with columns: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
        return buf.getvalue()

    st.download_button("⬇️ Download Excel Template", generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())
        ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box = st.slider("Box Size", 4, 20, 10, key="b_box")
        border = st.slider("Border", 2, 10, 4, key="b_border")
        fg = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style = st.radio("QR Style", ["square", "dots"], index=0, key="b_style")

        if st.button("Generate Batch ZIP"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    if not first and not last: continue
                    name_stub = sanitize_filename(f"{first}_{last}")
                    vcard = build_vcard(first, last,
                                        str(row.get("Organization", "")),
                                        str(row.get("Title", "")),
                                        str(row.get("Phone", "")),
                                        str(row.get("Mobile", "")),
                                        str(row.get("Email", "")),
                                        str(row.get("Website", "")),
                                        str(row.get("Notes", "")))
                    zf.writestr(f"{name_stub}/{name_stub}.vcf", vcard_bytes(vcard))
                    # png
                    img = make_qr_image(vcard, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{name_stub}/{name_stub}.png", png_buf.getvalue())
                    # svg
                    svg_img = make_qr_image(vcard, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{name_stub}/{name_stub}.svg", svg_buf.getvalue())
            zip_buf.seek(0)
            st.download_button("⬇️ Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"Batch_QR_vCards_{datetime.now().strftime('%Y%m%d')}.zip", mime="application/zip")

# --- WhatsApp ---
with tabs[2]:
    st.header("📱 WhatsApp QR")
    phone = st.text_input("Phone Number (with country code)")
    msg = st.text_area("Message (optional)")
    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="wa_ec")
    box = st.slider("Box Size", 4, 20, 10, key="wa_box")
    border = st.slider("Border", 2, 10, 4, key="wa_border")
    fg = st.color_picker("Foreground", "#25D366", key="wa_fg")
    bg = st.color_picker("Background", "#FFFFFF", key="wa_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="wa_style")
    if st.button("Generate WhatsApp QR"):
        link = f"https://wa.me/{phone}?text={quote_plus(msg)}"
        show_qr_result(link, f"whatsapp_{phone}", ec, box, border, fg, bg, style)

# --- Email ---
with tabs[3]:
    st.header("📧 Email QR")
    to = st.text_input("Recipient Email")
    subject = st.text_input("Subject")
    body = st.text_area("Body")
    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="em_ec")
    box = st.slider("Box Size", 4, 20, 10, key="em_box")
    border = st.slider("Border", 2, 10, 4, key="em_border")
    fg = st.color_picker("Foreground", "#0000FF", key="em_fg")
    bg = st.color_picker("Background", "#FFFFFF", key="em_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="em_style")
    if st.button("Generate Email QR"):
        mailto = f"mailto:{to}?subject={quote_plus(subject)}&body={quote_plus(body)}"
        show_qr_result(mailto, f"email_{sanitize_filename(to)}", ec, box, border, fg, bg, style)

# --- Link ---
with tabs[4]:
    st.header("🔗 URL QR")
    url = st.text_input("Website URL")
    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="ln_ec")
    box = st.slider("Box Size", 4, 20, 10, key="ln_box")
    border = st.slider("Border", 2, 10, 4, key="ln_border")
    fg = st.color_picker("Foreground", "#000000", key="ln_fg")
    bg = st.color_picker("Background", "#FFFFFF", key="ln_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="ln_style")
    if st.button("Generate Link QR"):
        show_qr_result(url, "link_qr", ec, box, border, fg, bg, style)

# --- Location ---
with tabs[5]:
    st.header("📍 Location QR")
    lat = st.text_input("Latitude")
    lon = st.text_input("Longitude")
    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="loc_ec")
    box = st.slider("Box Size", 4, 20, 10, key="loc_box")
    border = st.slider("Border", 2, 10, 4, key="loc_border")
    fg = st.color_picker("Foreground", "#FF0000", key="loc_fg")
    bg = st.color_picker("Background", "#FFFFFF", key="loc_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="loc_style")
    if st.button("Generate Location QR"):
        if lat and lon:
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            show_qr_result(maps_url, f"location_{lat}_{lon}", ec, box, border, fg, bg, style)
        else:
            st.warning("Please enter latitude and longitude.")

# --- Barcode ---
with tabs[6]:
    st.header("🏷 Product Barcode")
    if not BARCODE_AVAILABLE:
        st.error("❌ Barcode module not installed. Please check requirements.txt")
    else:
        code_text = st.text_input("Enter product code or text")
        barcode_type = st.selectbox("Barcode Format", ["code128", "ean13", "upc", "isbn13"])
        if st.button("Generate Barcode"):
            if not code_text.strip():
                st.warning("Please enter text")
            else:
                files = {}
                BARCODE_CLASS = barcode.get_barcode_class(barcode_type)
                png_buf = io.BytesIO()
                BARCODE_CLASS(code_text, writer=ImageWriter()).write(png_buf)
                png_buf.seek(0)
                files[f"{code_text}.png"] = png_buf.getvalue()
                st.image(png_buf.getvalue(), caption="Generated Barcode")
                st.download_button("⬇️ Download Barcode PNG", png_buf.getvalue(), f"{code_text}.png", "image/png")

                # SVG
                svg_buf = io.BytesIO()
                BARCODE_CLASS(code_text).write(svg_buf)
                files[f"{code_text}.svg"] = svg_buf.getvalue()
                st.download_button("⬇️ Download Barcode SVG", svg_buf.getvalue(), f"{code_text}.svg", "image/svg+xml")

                # ZIP
                st.download_button("⬇️ Download All (ZIP)", zip_files(files), f"{code_text}_barcode.zip", "application/zip")
