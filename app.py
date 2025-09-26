import io, re, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# Barcodes
try:
    import barcode
    from barcode.writer import ImageWriter, SVGWriter
    BARCODE_OK = True
except Exception:
    BARCODE_OK = False

st.set_page_config(page_title="QR & Barcode Suite", page_icon="🔳", layout="centered")

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
.stDownloadButton button, .stButton button {
    border-radius: 8px !important; background-color: #3A3A3A !important;
    color: #FFF !important; font-weight: 500 !important; border: none !important;
}
.stDownloadButton button:hover, .stButton button:hover { background-color: #1E1E1E !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def safe_name_keep_case(s: str) -> str:
    s = (s or "").strip().replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    return s or "contact"

def build_vcard(first, last, org, title, phone, mobile, email, website, notes, version="3.0"):
    """Keep your original vCard builder (3.0 / 4.0)."""
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
    # Dots style
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

def make_qr_outputs(data: str, fname: str, ec: str, box: int, border: int,
                    fg: str, bg: str, style: str):
    """Return (files_dict, png_bytes, svg_bytes) for one QR payload."""
    files = {}
    # PNG
    img_png = make_qr_image(data, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
    png_buf = io.BytesIO(); img_png.save(png_buf, format="PNG")
    png_bytes = png_buf.getvalue()
    files[f"{fname}.png"] = png_bytes
    # SVG
    img_svg = make_qr_image(data, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
    svg_buf = io.BytesIO(); img_svg.save(svg_buf)
    svg_bytes = svg_buf.getvalue()
    files[f"{fname}.svg"] = svg_bytes
    return files, png_bytes, svg_bytes

def zip_files(file_dict):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for fname, content in file_dict.items():
            zf.writestr(fname, content)
    zip_buf.seek(0)
    return zip_buf.getvalue()

def generate_batch_template_bytes():
    cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
    df = pd.DataFrame(columns=cols)
    buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
    return buf.getvalue()

def generate_employee_template_bytes():
    cols = ["First Name","Last Name","Phone","Email","Company","Job Title","Website","Department","Location"]
    df = pd.DataFrame(columns=cols)
    buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Employees"); buf.seek(0)
    return buf.getvalue()

# =========================
# UI
# =========================
st.title("🔳 QR & Barcode Suite")

tabs = st.tabs([
    "vCard Single",        # 0
    "Batch Mode",          # 1
    "WhatsApp",            # 2
    "Email",               # 3
    "Link",                # 4
    "Location",            # 5
    "Product Barcode",     # 6 (new)
    "Employee Directory"   # 7 (new)
])

# --- vCard Single ---
with tabs[0]:
    st.header("Single vCard Generator")
    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0, key="v1_ver")
    first = st.text_input("First Name", key="v1_first")
    last  = st.text_input("Last Name", key="v1_last")
    org   = st.text_input("Organization", key="v1_org")
    title = st.text_input("Title", key="v1_title")
    phone = st.text_input("Phone", key="v1_phone")
    mobile= st.text_input("Mobile", key="v1_mobile")
    email = st.text_input("Email", key="v1_email")
    website= st.text_input("Website", key="v1_website")
    notes = st.text_area("Notes", key="v1_notes")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="v1_ec")
    box= st.slider("Box Size", 4, 20, 10, key="v1_box")
    border= st.slider("Border", 2, 10, 4, key="v1_border")
    fg = st.color_picker("QR Foreground", "#000000", key="v1_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="v1_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="v1_style")

    if st.button("Generate vCard & QR", key="v1_btn"):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes, version)
        fname = sanitize_filename(f"{first}_{last}")
        files = {}
        vcf_bytes = vcard_bytes(vcard); files[f"{fname}.vcf"] = vcf_bytes
        qr_files, png_bytes, svg_bytes = make_qr_outputs(vcard, fname, ec, box, border, fg, bg, style)
        files.update(qr_files)

        st.image(png_bytes, caption="QR Code")
        st.download_button("⬇️ vCard (.vcf)", vcf_bytes, f"{fname}.vcf", "text/vcard", key="v1_dl_vcf")
        st.download_button("⬇️ QR PNG", png_bytes, f"{fname}.png", "image/png", key="v1_dl_png")
        st.download_button("⬇️ QR SVG", svg_bytes, f"{fname}.svg", "image/svg+xml", key="v1_dl_svg")
        st.download_button("⬇️ All (ZIP)", zip_files(files), f"{fname}_all.zip", "application/zip", key="v1_dl_zip")

# --- Batch Mode ---
with tabs[1]:
    st.header("Batch Mode (Excel Upload)")
    st.download_button("⬇️ Download Excel Template", data=generate_batch_template_bytes(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="b_tpl")

    excel_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], key="b_file")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box = st.slider("Box Size", 4, 20, 10, key="b_box")
        border = st.slider("Border", 2, 10, 4, key="b_border")
        fg = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style = st.radio("QR Style", ["square", "dots"], index=0, key="b_style")

        root_label = st.text_input("Root folder name", value="Batch_QR_vCards", key="b_root")
        today_str = datetime.now().strftime("%Y%m%d")
        root_folder = f"{(root_label or 'Batch_QR_vCards')}_{today_str}"

        if st.button("Generate Batch ZIP", key="b_btn"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    if not first and not last:
                        continue
                    name_stub = safe_name_keep_case(f"{first}_{last}".strip("_"))
                    vcard = build_vcard(first, last,
                                        str(row.get("Organization", "")),
                                        str(row.get("Title", "")),
                                        str(row.get("Phone", "")),
                                        str(row.get("Mobile", "")),
                                        str(row.get("Email", "")),
                                        str(row.get("Website", "")),
                                        str(row.get("Notes", "")))
                    # vcf
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.vcf", vcard_bytes(vcard))
                    # png
                    img = make_qr_image(vcard, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
                    pbuf = io.BytesIO(); img.save(pbuf, format="PNG")
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.png", pbuf.getvalue())
                    # svg
                    svg_img = make_qr_image(vcard, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
                    sbuf = io.BytesIO(); svg_img.save(sbuf)
                    zf.writestr(f"{root_folder}/{name_stub}/{name_stub}.svg", sbuf.getvalue())
            zip_buf.seek(0)
            st.download_button("⬇️ Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{root_folder}.zip", mime="application/zip", key="b_dl_zip")

# --- WhatsApp ---
with tabs[2]:
    st.header("WhatsApp QR")
    wa_num = st.text_input("WhatsApp Number (digits only, intl format)", key="wa_num")
    wa_msg = st.text_input("Prefilled Message (optional)", key="wa_msg")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="wa_ec")
    box = st.slider("Box Size", 4, 20, 10, key="wa_box")
    border = st.slider("Border", 2, 10, 4, key="wa_border")
    fg = st.color_picker("QR Foreground", "#25D366", key="wa_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="wa_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="wa_style")

    if st.button("Generate WhatsApp QR", key="wa_btn"):
        wa_url = f"https://wa.me/{wa_num}"
        if wa_msg:
            wa_url += f"?text={quote_plus(wa_msg)}"
        fname = f"whatsapp_{sanitize_filename(wa_num)}"
        files, png_bytes, svg_bytes = make_qr_outputs(wa_url, fname, ec, box, border, fg, bg, style)
        st.image(png_bytes, caption="WhatsApp QR")
        st.download_button("⬇️ PNG", png_bytes, f"{fname}.png", "image/png", key="wa_dl_png")
        st.download_button("⬇️ SVG", svg_bytes, f"{fname}.svg", "image/svg+xml", key="wa_dl_svg")
        st.download_button("⬇️ All (ZIP)", zip_files(files), f"{fname}.zip", "application/zip", key="wa_dl_zip")

# --- Email ---
with tabs[3]:
    st.header("Email QR")
    mail_to = st.text_input("Recipient", key="em_to")
    mail_sub = st.text_input("Subject", key="em_sub")
    mail_body = st.text_area("Body", key="em_body")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="em_ec")
    box = st.slider("Box Size", 4, 20, 10, key="em_box")
    border = st.slider("Border", 2, 10, 4, key="em_border")
    fg = st.color_picker("QR Foreground", "#0000FF", key="em_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="em_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="em_style")

    if st.button("Generate Email QR", key="em_btn"):
        params = []
        if mail_sub: params.append("subject=" + quote_plus(mail_sub))
        if mail_body: params.append("body=" + quote_plus(mail_body))
        mailto_url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
        fname = f"email_{sanitize_filename(mail_to)}"
        files, png_bytes, svg_bytes = make_qr_outputs(mailto_url, fname, ec, box, border, fg, bg, style)
        st.image(png_bytes, caption="Email QR")
        st.download_button("⬇️ PNG", png_bytes, f"{fname}.png", "image/png", key="em_dl_png")
        st.download_button("⬇️ SVG", svg_bytes, f"{fname}.svg", "image/svg+xml", key="em_dl_svg")
        st.download_button("⬇️ All (ZIP)", zip_files(files), f"{fname}.zip", "application/zip", key="em_dl_zip")

# --- Link ---
with tabs[4]:
    st.header("Link QR")
    link_url = st.text_input("Enter URL", key="ln_url")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="ln_ec")
    box = st.slider("Box Size", 4, 20, 10, key="ln_box")
    border = st.slider("Border", 2, 10, 4, key="ln_border")
    fg = st.color_picker("QR Foreground", "#000000", key="ln_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="ln_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="ln_style")

    if st.button("Generate Link QR", key="ln_btn"):
        url = (link_url or "").strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        fname = "link_qr"
        files, png_bytes, svg_bytes = make_qr_outputs(url, fname, ec, box, border, fg, bg, style)
        st.image(png_bytes, caption="Link QR")
        st.download_button("⬇️ PNG", png_bytes, f"{fname}.png", "image/png", key="ln_dl_png")
        st.download_button("⬇️ SVG", svg_bytes, f"{fname}.svg", "image/svg+xml", key="ln_dl_svg")
        st.download_button("⬇️ All (ZIP)", zip_files(files), f"{fname}.zip", "application/zip", key="ln_dl_zip")

# --- Location ---
with tabs[5]:
    st.header("Location QR")
    lat = st.text_input("Latitude", key="loc_lat")
    lon = st.text_input("Longitude", key="loc_lon")
    gmap_link = st.text_input("Google Maps Link (optional)", key="loc_gmap")

    ec = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="loc_ec")
    box = st.slider("Box Size", 4, 20, 10, key="loc_box")
    border = st.slider("Border", 2, 10, 4, key="loc_border")
    fg = st.color_picker("QR Foreground", "#FF0000", key="loc_fg")
    bg = st.color_picker("QR Background", "#FFFFFF", key="loc_bg")
    style = st.radio("QR Style", ["square", "dots"], index=0, key="loc_style")

    if st.button("Generate Location QR", key="loc_btn"):
        if gmap_link.strip():
            loc_url = gmap_link.strip()
        elif lat and lon:
            loc_url = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            st.warning("Please provide either latitude & longitude or a Google Maps link.")
            loc_url = ""
        if loc_url:
            fname = "location_qr"
            files, png_bytes, svg_bytes = make_qr_outputs(loc_url, fname, ec, box, border, fg, bg, style)
            st.image(png_bytes, caption="Location QR")
            st.download_button("⬇️ PNG", png_bytes, f"{fname}.png", "image/png", key="loc_dl_png")
            st.download_button("⬇️ SVG", svg_bytes, f"{fname}.svg", "image/svg+xml", key="loc_dl_svg")
            st.download_button("⬇️ All (ZIP)", zip_files(files), f"{fname}.zip", "application/zip", key="loc_dl_zip")

# --- Product Barcode (NEW) ---
with tabs[6]:
    st.header("🏷 Product Barcode")
    if not BARCODE_OK:
        st.error("`python-barcode` not installed. Add it to requirements.txt and redeploy.")
    else:
        code_text = st.text_input("Enter product code / text", key="bc_text")
        barcode_type = st.selectbox("Barcode Format", ["code128", "ean13", "upc"], key="bc_type")
        if st.button("Generate Barcode", key="bc_btn"):
            if not code_text.strip():
                st.warning("Please enter text")
            else:
                files = {}
                try:
                    BAR = barcode.get_barcode_class(barcode_type)
                    # PNG
                    png_buf = io.BytesIO()
                    BAR(code_text, writer=ImageWriter()).write(png_buf)
                    png_bytes = png_buf.getvalue()
                    files[f"{code_text}.png"] = png_bytes
                    st.image(png_bytes, caption=f"{barcode_type.upper()} Barcode")
                except Exception as e:
                    st.error(f"PNG generation error: {e}")
                try:
                    # SVG
                    svg_buf = io.BytesIO()
                    BAR(code_text, writer=SVGWriter()).write(svg_buf)
                    svg_bytes = svg_buf.getvalue()
                    files[f"{code_text}.svg"] = svg_bytes
                    st.download_button("⬇️ SVG", svg_bytes, f"{code_text}.svg", "image/svg+xml", key="bc_dl_svg")
                except Exception as e:
                    st.error(f"SVG generation error: {e}")
                if "png_bytes" in locals():
                    st.download_button("⬇️ PNG", png_bytes, f"{code_text}.png", "image/png", key="bc_dl_png")
                if files:
                    st.download_button("⬇️ All (ZIP)", zip_files(files), f"{sanitize_filename(code_text)}_barcode.zip", "application/zip", key="bc_dl_zip")

# --- Employee Directory (NEW) ---
with tabs[7]:
    st.header("🧑‍💼 Employee Directory")
    st.caption("Template includes Department & Location. Outputs per-employee folder with .vcf + QR .png + .svg")

    st.download_button("⬇️ Download Employee Excel Template",
                       generate_employee_template_bytes(),
                       file_name="employee_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="emp_tpl")

    excel_emp = st.file_uploader("Upload filled employee template (.xlsx)", type=["xlsx"], key="emp_file")
    version_emp = st.selectbox("vCard Version for employees", ["3.0", "4.0"], index=0, key="emp_ver")

    ec_e = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="emp_ec")
    box_e = st.slider("Box Size", 4, 20, 10, key="emp_box")
    border_e = st.slider("Border", 2, 10, 4, key="emp_border")
    fg_e = st.color_picker("QR Foreground", "#000000", key="emp_fg")
    bg_e = st.color_picker("QR Background", "#FFFFFF", key="emp_bg")
    style_e = st.radio("QR Style", ["square", "dots"], index=0, key="emp_style")

    if excel_emp and st.button("Generate Employee Directory ZIP", key="emp_btn"):
        df = pd.read_excel(excel_emp)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                first = str(row.get("First Name", "")).strip()
                last  = str(row.get("Last Name", "")).strip()
                if not first and not last:
                    continue
                company = str(row.get("Company","")).strip()
                title   = str(row.get("Job Title","")).strip()
                website = str(row.get("Website","")).strip()
                phone   = str(row.get("Phone","")).strip()
                email   = str(row.get("Email","")).strip()
                dept    = str(row.get("Department","")).strip()
                loc     = str(row.get("Location","")).strip()

                # preserve Department & Location in NOTE
                note_parts = []
                if dept: note_parts.append(f"Department: {dept}")
                if loc:  note_parts.append(f"Location: {loc}")
                notes = " | ".join(note_parts)

                vcard = build_vcard(first, last, company, title, phone, "", email, website, notes, version_emp)
                name_stub = safe_name_keep_case(f"{first}_{last}".strip("_"))

                zf.writestr(f"{name_stub}/{name_stub}.vcf", vcard_bytes(vcard))

                img_png = make_qr_image(vcard, ec_e, box_e, border_e, as_svg=False, fg_color=fg_e, bg_color=bg_e, style=style_e)
                pbuf = io.BytesIO(); img_png.save(pbuf, format="PNG")
                zf.writestr(f"{name_stub}/{name_stub}.png", pbuf.getvalue())

                img_svg = make_qr_image(vcard, ec_e, box_e, border_e, as_svg=True, fg_color=fg_e, bg_color=bg_e, style=style_e)
                sbuf = io.BytesIO(); img_svg.save(sbuf)
                zf.writestr(f"{name_stub}/{name_stub}.svg", sbuf.getvalue())

        zip_buf.seek(0)
        st.success("Employee directory generated.")
        st.download_button("⬇️ Download All Employees (ZIP)", zip_buf.getvalue(),
                           file_name=f"Employee_Directory_{datetime.now().strftime('%Y%m%d')}.zip",
                           mime="application/zip", key="emp_dl_zip")
