# app.py
import io, re, zipfile
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import (
    ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
)

st.set_page_config(page_title="QR Generator Suite", page_icon="🔳", layout="centered")

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(
    first, last, org, title, phone, mobile, email, website, notes,
    version="3.0", photo_url=""
):
    if version == "4.0":
        lines = ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{(first + ' ' + last).strip()}")
        if org:     lines.append(f"ORG:{org}")
        if title:   lines.append(f"TITLE:{title}")
        if phone:   lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile:  lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email:   lines.append(f"EMAIL:{email}")
        if website: lines.append(f"URL:{website}")
        if photo_url:
            # Reference external image (URL). Devices that support vCard PHOTO will try to fetch it.
            lines.append(f"PHOTO:{photo_url}")
        if notes:
            lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    else:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last};{first};;;")
        lines.append(f"FN:{(first + ' ' + last).strip()}")
        if org:     lines.append(f"ORG:{org}")
        if title:   lines.append(f"TITLE:{title}")
        if phone:   lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile:  lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email:   lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website: lines.append(f"URL:{website}")
        if photo_url:
            lines.append(f"PHOTO:{photo_url}")
        if notes:
            lines.append(f"NOTE:{notes}")
        lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard_str: str) -> bytes:
    # CRLF per spec
    return vcard_str.replace("\n", "\r\n").encode("utf-8")

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

def make_qr_image(
    data: str, ec_label: str, box_size: int, border: int, as_svg: bool,
    fg_color="#000000", bg_color="#FFFFFF", style="square"
):
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
    # dots style for PNG
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

def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url

def split_multi_numbers(s: str):
    """Split by comma, space or newline; keep digits and + only."""
    if not s:
        return []
    raw = re.split(r"[,\s]+", s.strip())
    out = []
    for item in raw:
        if not item:
            continue
        # Keep + and digits only
        num = re.sub(r"[^\d+]", "", item)
        if num:
            out.append(num)
    return out

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
# Main App
# =========================
st.title("QR Generator Suite")

tabs = st.tabs(["vCard Single", "Batch Mode", "WhatsApp", "Email", "Link", "Location"])

# --- vCard Single ---
with tabs[0]:
    st.header("Single vCard Generator")

    # Inputs
    col1, col2 = st.columns(2)
    with col1:
        first   = st.text_input("First Name")
        org     = st.text_input("Organization")
        phone   = st.text_input("Phone (Work)")
        email   = st.text_input("Email")
        website = st.text_input("Website")
    with col2:
        last    = st.text_input("Last Name")
        title   = st.text_input("Title")
        mobile  = st.text_input("Mobile")
        notes   = st.text_area("Notes")
        photo_url = st.text_input("Photo URL (optional)")

    # QR settings
    st.subheader("QR Settings")
    ec     = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
    box    = st.slider("Box Size", 4, 20, 10)
    border = st.slider("Border", 2, 10, 4)
    fg     = st.color_picker("QR Foreground", "#000000")
    bg     = st.color_picker("QR Background", "#FFFFFF")
    style  = st.radio("QR Style", ["square", "dots"], index=0)

    # vCard versioning
    st.subheader("vCard Output")
    version = st.selectbox("Primary vCard Version", ["3.0", "4.0"], index=0)
    gen_both = st.checkbox("Also generate the other version", value=False)

    if st.button("Generate vCard & QR"):
        # Primary vCard
        vcard_main = build_vcard(first, last, org, title, phone, mobile, email, website, notes, version, photo_url)
        fname = sanitize_filename(f"{first}_{last}") or "contact"

        # vCard downloads
        st.download_button("Download vCard (.vcf)", data=vcard_bytes(vcard_main),
                           file_name=f"{fname}.vcf", mime="text/vcard")

        # Optional secondary vCard
        if gen_both:
            other_version = "4.0" if version == "3.0" else "3.0"
            vcard_other = build_vcard(first, last, org, title, phone, mobile, email, website, notes, other_version, photo_url)
            st.download_button(f"Download vCard {other_version} (.vcf)",
                               data=vcard_bytes(vcard_other),
                               file_name=f"{fname}_v{other_version.replace('.','')}.vcf",
                               mime="text/vcard")

        # PNG QR
        img = make_qr_image(vcard_main, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.image(png_buf.getvalue(), caption="QR Code")
        st.download_button("Download QR PNG", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png")

        # SVG QR
        svg_img = make_qr_image(vcard_main, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("Download QR SVG", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml")

# --- Batch Mode ---
with tabs[1]:
    st.header("Batch Mode (Excel Upload)")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes", "Photo URL"]
        df = pd.DataFrame(columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0)
        return buf.getvalue()

    st.download_button("Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Per-contact subfolder pattern
    st.caption("Subfolder pattern tokens: {first}, {last}, {org}, {title}")
    folder_pattern = st.text_input("Per-contact subfolder name pattern", value="{first}_{last}")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name (optional)")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

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
            names_ok = []
            names_missing = []
            total_files = 0

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()

                    if not first and not last:
                        names_missing.append("(missing name row)")
                        continue

                    org   = str(row.get("Organization", "")).strip()
                    title = str(row.get("Title", "")).strip()
                    phone = str(row.get("Phone", "")).strip()
                    mobile= str(row.get("Mobile", "")).strip()
                    email = str(row.get("Email", "")).strip()
                    web   = str(row.get("Website", "")).strip()
                    notes = str(row.get("Notes", "")).strip()
                    photo_url = str(row.get("Photo URL", "")).strip()

                    # Per-contact folder name via pattern
                    folder_name = folder_pattern.format(
                        first=sanitize_filename(first),
                        last=sanitize_filename(last),
                        org=sanitize_filename(org),
                        title=sanitize_filename(title),
                    ) or "contact"

                    vcard = build_vcard(first, last, org, title, phone, mobile, email, web, notes, "3.0", photo_url)

                    # Write VCF
                    zf.writestr(f"{batch_folder}/{folder_name}/{folder_name}.vcf", vcard_bytes(vcard))

                    # PNG
                    img = make_qr_image(vcard, ec, box, border, as_svg=False, fg_color=fg, bg_color=bg, style=style)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{folder_name}/{folder_name}_qr.png", png_buf.getvalue())

                    # SVG
                    svg_img = make_qr_image(vcard, ec, box, border, as_svg=True, fg_color=fg, bg_color=bg, style=style)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{folder_name}/{folder_name}_qr.svg", svg_buf.getvalue())

                    names_ok.append(f"{first} {last}".strip())
                    total_files += 3

                # Summary report
                summary_lines = [
                    "Batch Export Summary",
                    "---------------------",
                    f"Batch Folder: {batch_folder}",
                    f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Contacts processed: {len(names_ok)}",
                    f"Rows skipped (missing names): {len(names_missing)}",
                    f"Files/contact: 3 (VCF, PNG, SVG)",
                    f"Total files in ZIP: {total_files}",
                    "",
                    "Contacts:",
                ] + [f"- {n}" for n in names_ok]

                if names_missing:
                    summary_lines += ["", "Missing name rows:", *[f"- {m}" for m in names_missing]]

                zf.writestr(f"{batch_folder}/SUMMARY.txt", "\n".join(summary_lines))

            zip_buf.seek(0)
            st.download_button("Download Batch ZIP", data=zip_buf.getvalue(),
                               file_name=f"{batch_folder}.zip", mime="application/zip")

            # Show brief summary in UI
            st.success(f"Done! Contacts: {len(names_ok)} | Skipped: {len(names_missing)} | Files: {total_files}")

# --- WhatsApp ---
with tabs[2]:
    st.header("WhatsApp QR (Multiple)")

    wa_numbers_raw = st.text_area(
        "WhatsApp Numbers (comma/space/newline separated, intl format; + optional)",
        placeholder="9665xxxxxxx, +9665yyyyyyy"
    )
    wa_msg = st.text_input("Prefilled Message (optional, Arabic/English supported)")

    if st.button("Generate WhatsApp ZIP"):
        numbers = split_multi_numbers(wa_numbers_raw)
        if not numbers:
            st.warning("Add at least one WhatsApp number.")
        else:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for num in numbers:
                    url = f"https://wa.me/{num}"
                    if wa_msg:
                        # quote_plus handles Arabic and spaces safely
                        url += f"?text={quote_plus(wa_msg)}"
                    img = make_qr_image(url, "M (15%)", 10, 4, as_svg=False)
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    safe = sanitize_filename(num)
                    zf.writestr(f"whatsapp_qr/{safe}.png", buf.getvalue())
            zip_buf.seek(0)
            st.download_button("Download WhatsApp QR ZIP", data=zip_buf.getvalue(),
                               file_name="whatsapp_qr_codes.zip", mime="application/zip")

# --- Email ---
with tabs[3]:
    st.header("Email QR")

    col1, col2 = st.columns(2)
    with col1:
        mail_to  = st.text_input("To")
        mail_cc  = st.text_input("CC (comma separated)", placeholder="cc1@example.com, cc2@example.com")
    with col2:
        mail_bcc = st.text_input("BCC (comma separated)", placeholder="hidden1@example.com, hidden2@example.com")

    # Subject templates
    templates = [
        "Inquiry from QR",
        "Contact request",
        "Meeting request",
        "Support request",
        "Custom…",
    ]
    sub_choice = st.selectbox("Subject Template", templates, index=0)
    custom_sub = st.text_input("Custom Subject (if 'Custom…' selected)", value="") if sub_choice == "Custom…" else ""

    mail_body = st.text_area("Body")

    if st.button("Generate Email QR"):
        subject = custom_sub if sub_choice == "Custom…" else sub_choice
        params = []
        if subject:  params.append("subject=" + quote_plus(subject))
        if mail_body: params.append("body=" + quote_plus(mail_body))
        if mail_cc.strip():
            params.append("cc=" + quote_plus(",".join([x.strip() for x in mail_cc.split(",") if x.strip()])))
        if mail_bcc.strip():
            params.append("bcc=" + quote_plus(",".join([x.strip() for x in mail_bcc.split(",") if x.strip()])))
        mailto_url = f"mailto:{mail_to.strip()}" + (("?" + "&".join(params)) if params else "")

        img = make_qr_image(mailto_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Email QR")
        st.download_button("Email QR (PNG)", data=buf.getvalue(),
                           file_name="email_qr.png", mime="image/png")

# --- Link ---
with tabs[4]:
    st.header("Link QR")

    link_url = st.text_input("Enter URL")
    auto_fix = st.checkbox("Auto-fix scheme (add https:// if missing)", value=True)
    pretend_shorten = st.checkbox("Prefer short link (no external service; encodes original link)", value=True)

    if st.button("Generate Link QR"):
        url = link_url.strip()
        if auto_fix:
            url = normalize_url(url)
        # "Shorten" is a UX toggle only; we still encode the actual URL (no external call)
        img = make_qr_image(url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Link QR")
        st.download_button("Link QR (PNG)", data=buf.getvalue(),
                           file_name="link_qr.png", mime="image/png")

# --- Location ---
with tabs[5]:
    st.header("Location QR")

    provider = st.radio("Maps Provider", ["Google Maps", "Apple Maps"], index=0)
    st.caption("You can provide a place name, or latitude/longitude, or a full Google Maps link.")
    place_name = st.text_input("Place name (optional)")
    lat = st.text_input("Latitude (optional)")
    lon = st.text_input("Longitude (optional)")
    gmap_link = st.text_input("Google Maps Link (optional)")

    if st.button("Generate Location QR"):
        loc_url = ""
        if provider == "Google Maps":
            if gmap_link.strip():
                loc_url = gmap_link.strip()
            elif place_name.strip():
                loc_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(place_name.strip())}"
            elif lat and lon:
                loc_url = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            # Apple Maps
            if place_name.strip():
                loc_url = f"http://maps.apple.com/?q={quote_plus(place_name.strip())}"
            elif lat and lon:
                loc_url = f"http://maps.apple.com/?q={lat},{lon}"

        if not loc_url:
            st.warning("Provide either a place name, a Google Maps link, or both latitude & longitude.")
        else:
            img = make_qr_image(loc_url, "M (15%)", 10, 4, as_svg=False)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Location QR")
            st.download_button("Location QR (PNG)", data=buf.getvalue(),
                               file_name="location_qr.png", mime="image/png")

# =========================
# Footer
# =========================
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain | <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
