import io, re, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
import barcode
from barcode.writer import ImageWriter, SVGWriter

st.set_page_config(page_title="QR & Barcode Generator Suite", page_icon="🔳", layout="centered")

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
st.title("🔳 QR & Barcode Generator Suite")

tabs = st.tabs([
    "vCard Single", 
    "Batch Mode", 
    "WhatsApp", 
    "Email", 
    "Link", 
    "Location",
    "Product Barcode",
    "Employee Directory"
])

# --- Product Barcode ---
with tabs[6]:
    st.header("🏷 Product Barcode")
    code_text = st.text_input("Enter product code or text")
    barcode_type = st.selectbox("Barcode Format", ["code128", "ean13", "upc"])
    if st.button("Generate Barcode"):
        if not code_text.strip():
            st.warning("Please enter text")
        else:
            try:
                # PNG
                png_buf = io.BytesIO()
                bc_class = barcode.get_barcode_class(barcode_type)
                bc = bc_class(code_text, writer=ImageWriter())
                bc.write(png_buf)
                png_bytes = png_buf.getvalue()

                # SVG
                svg_buf = io.BytesIO()
                bc_svg = bc_class(code_text, writer=SVGWriter())
                bc_svg.write(svg_buf)
                svg_bytes = svg_buf.getvalue()

                # Show + download
                st.image(png_bytes, caption="Generated Barcode")
                st.download_button("⬇️ Download PNG", png_bytes, f"{code_text}.png", "image/png")
                st.download_button("⬇️ Download SVG", svg_bytes, f"{code_text}.svg", "image/svg+xml")
            except Exception as e:
                st.error(f"Error: {e}")

# --- Employee Directory ---
with tabs[7]:
    st.header("👥 Employee Directory")

    def generate_employee_template():
        cols = ["First Name", "Last Name", "Phone", "Email", "Company", "Job Title", "Website", "Department", "Location"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, sheet_name="Employees")
        buf.seek(0)
        return buf.getvalue()

    st.download_button("⬇️ Download Employee Excel Template", data=generate_employee_template(),
                       file_name="employee_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    emp_file = st.file_uploader("Upload Filled Employee Excel", type=["xlsx"])
    if emp_file:
        df = pd.read_excel(emp_file)
        st.write("Preview:", df.head())
        if st.button("Generate Employee Directory ZIP"):
            processed = 0
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    if not first and not last:
                        continue
                    fname = sanitize_filename(f"{first}_{last}")
                    vcard = build_vcard(first, last,
                                        str(row.get("Company", "")),
                                        str(row.get("Job Title", "")),
                                        str(row.get("Phone", "")),
                                        "",
                                        str(row.get("Email", "")),
                                        str(row.get("Website", "")),
                                        f"Department: {row.get('Department','')}, Location: {row.get('Location','')}")
                    # vcf
                    zf.writestr(f"{fname}/{fname}.vcf", vcard_bytes(vcard))
                    # png
                    img = make_qr_image(vcard, "H (30%)", 10, 4, as_svg=False)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{fname}/{fname}.png", png_buf.getvalue())
                    # svg
                    svg_img = make_qr_image(vcard, "H (30%)", 10, 4, as_svg=True)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{fname}/{fname}.svg", svg_buf.getvalue())
                    processed += 1
            zip_buf.seek(0)
            st.download_button("⬇️ Download Employee Directory ZIP", data=zip_buf.getvalue(),
                               file_name="employee_directory.zip", mime="application/zip")
            st.success(f"Done! {processed} employees processed.")
# =========================