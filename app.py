# app.py
import io, re, zipfile, base64
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# =========================
# Helpers
# =========================
def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard(first, last, org, title, phone, mobile, email, website, notes):
    """vCard 3.0 for broad compatibility (no addresses/timezones)."""
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    lines.append(f"N:{last};{first};;;")
    lines.append(f"FN:{first} {last}".strip())
    if org:     lines.append(f"ORG:{org}")
    if title:   lines.append(f"TITLE:{title}")
    if phone:   lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
    if mobile:  lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
    if email:   lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
    if website: lines.append(f"URL:{website}")
    if notes:   lines.append(f"NOTE:{notes}")
    lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard: str) -> bytes:
    # Windows contacts like CRLF
    return vcard.replace("\n", "\r\n").encode("utf-8")

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

def make_qr_image(
    data: str, ec_label: str, box_size: int, border: int,
    as_svg: bool, fg_color="#000000", bg_color="#FFFFFF", style="square"
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

    # custom dots / rounded for PNG
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
                    radius=radius, fill=fg_color
                )
    return img

# =========================
# Styling (neutral & minimal)
# =========================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'PingAR LT Regular', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
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
hr { border: none; border-top: 1px solid #EAEAEA; margin: 2rem 0; }
</style>
""", unsafe_allow_html=True)

# =========================
# Tabs
# =========================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Multi-QR Actions"])

# ==============================================================
# SINGLE MODE
# ==============================================================
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    col1, col2 = st.columns(2)
    with col1:
        first = st.text_input("First Name", key="single_first")
        phone = st.text_input("Phone (Work)", "8001249000", key="single_phone")
        email = st.text_input("Email", key="single_email")
        org   = st.text_input("Organization", key="single_org")
    with col2:
        last  = st.text_input("Last Name", key="single_last")
        mobile= st.text_input("Mobile", "+966", key="single_mobile")
        website = st.text_input("Website", key="single_website")
        title = st.text_input("Title", key="single_title")

    notes = st.text_area("Notes", key="single_notes")

    st.subheader("QR Settings")
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="single_ec")
    box_size = st.slider("Box Size (px/module)", 4, 20, 10, key="single_box")
    border   = st.slider("Border (modules)", 2, 10, 4, key="single_border")
    fg_color = st.color_picker("QR Foreground", "#000000", key="single_fg")
    bg_color = st.color_picker("QR Background", "#FFFFFF", key="single_bg")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="single_style")

    if st.button("Generate vCard & QR", key="single_btn"):
        vcard = build_vcard(first, last, org, title, phone, mobile, email, website, notes)
        fname = sanitize_filename(f"{first}_{last}") or "contact"

        # vCard file
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard", key="single_dl_vcf")

        # QR PNG
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(png_buf.getvalue(), caption="QR Code")
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download QR (PNG)", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png", key="single_dl_png")

        # QR SVG
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR (SVG)", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml", key="single_dl_svg")

        # ZIP bundle
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr(f"{fname}/{fname}.vcf", vcard_bytes(vcard))
            zf.writestr(f"{fname}/{fname}_qr.png", png_buf.getvalue())
            zf.writestr(f"{fname}/{fname}_qr.svg", svg_buf.getvalue())
        zip_buf.seek(0)
        st.download_button("📦 Download All (ZIP)", data=zip_buf.getvalue(),
                           file_name=f"{fname}_bundle.zip", mime="application/zip", key="single_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# BATCH MODE
# ==============================================================
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Batch Mode (Excel Upload)")
    st.caption("Excel columns required: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame([{
            "First Name": "Ali", "Last Name": "Saud", "Phone": "8001249000",
            "Mobile": "+966500000000", "Email": "ali@example.com",
            "Website": "https://example.com", "Organization": "Sales Dept",
            "Title": "Manager", "Notes": "VIP Client"
        }], columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template")
        buf.seek(0); return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="batch_template")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name (optional)", key="batch_parent")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="batch_upload")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec_label_b = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="batch_ec")
        box_size_b = st.slider("Box Size", 4, 20, 10, key="batch_box")
        border_b   = st.slider("Border", 2, 10, 4, key="batch_border")
        fg_b = st.color_picker("QR Foreground", "#000000", key="batch_fg")
        bg_b = st.color_picker("QR Background", "#FFFFFF", key="batch_bg")
        style_b = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="batch_style")

        if st.button("Generate Batch ZIP", key="batch_btn"):
            names = []
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    fname = sanitize_filename(f"{first}_{last}") or "contact"
                    names.append(f"{first} {last}".strip())

                    vcard = build_vcard(
                        first, last,
                        str(row.get("Organization", "")),
                        str(row.get("Title", "")),
                        str(row.get("Phone", "")),
                        str(row.get("Mobile", "")),
                        str(row.get("Email", "")),
                        str(row.get("Website", "")),
                        str(row.get("Notes", "")),
                    )

                    # Files
                    zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcard_bytes(vcard))

                    img = make_qr_image(vcard, ec_label_b, box_size_b, border_b, as_svg=False,
                                        fg_color=fg_b, bg_color=bg_b, style=style_b)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", png_buf.getvalue())

                    svg_img = make_qr_image(vcard, ec_label_b, box_size_b, border_b, as_svg=True)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

                # Summary
                summary = [
                    "Batch Export Summary", "---------------------",
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
                               key="batch_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# MULTI-QR ACTIONS (generate many QRs at once)
# ==============================================================
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Multi-QR Action Hub")
    st.caption("Fill in what you need and generate multiple QR codes at once. Download individually or as one ZIP.")

    # -------- Inputs
    colA, colB = st.columns(2)
    with colA:
        a_first   = st.text_input("First Name", key="act_first")
        a_phone   = st.text_input("Phone (Work)", key="act_phone")
        a_email   = st.text_input("Email", key="act_email")
        a_wa      = st.text_input("WhatsApp (digits only, intl)", key="act_wa")
        a_sms     = st.text_input("SMS Number (intl with +)", key="act_sms")
    with colB:
        a_last    = st.text_input("Last Name", key="act_last")
        a_mobile  = st.text_input("Mobile", key="act_mobile")
        a_website = st.text_input("Website", key="act_site")
        a_mail_sub= st.text_input("Email Subject (optional)", key="act_mail_sub")
        a_mail_body=st.text_area("Email Body (optional)", key="act_mail_body", height=80)

    a_org   = st.text_input("Organization", key="act_org")
    a_title = st.text_input("Title", key="act_title")
    a_notes = st.text_area("Notes (vCard only)", key="act_notes", height=80)

    st.subheader("Select Actions to Generate")
    cols_actions = st.columns(3)
    with cols_actions[0]:
        gen_vcard   = st.checkbox("vCard", value=True, key="act_ck_vcard")
        gen_call    = st.checkbox("Call (tel:)", value=True, key="act_ck_call")
    with cols_actions[1]:
        gen_whatsapp= st.checkbox("WhatsApp", value=True, key="act_ck_wa")
        gen_email   = st.checkbox("Email (mailto:)", value=True, key="act_ck_mail")
    with cols_actions[2]:
        gen_website = st.checkbox("Website (URL)", value=True, key="act_ck_site")
        gen_sms     = st.checkbox("SMS", value=False, key="act_ck_sms")

    st.subheader("QR Settings")
    ec_act   = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=2, key="act_ec")
    box_act  = st.slider("Box Size", 4, 20, 10, key="act_box")
    border_act=st.slider("Border", 2, 10, 4, key="act_border")
    fg_act   = st.color_picker("QR Foreground", "#000000", key="act_fg")
    bg_act   = st.color_picker("QR Background", "#FFFFFF", key="act_bg")
    style_act= st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="act_style")

    grp_name_default = f"{(a_first+'_'+a_last).strip('_') or 'contact'}_{datetime.now().strftime('%Y%m%d')}"
    group_name = st.text_input("Folder name for the ZIP (optional)", value=grp_name_default, key="act_group")

    # -------- Build everything on click
    if st.button("Generate All QRs", key="act_btn"):
        outputs = []  # list of dicts: {label, content, png_bytes, svg_bytes, filename}
        base_stub = sanitize_filename(f"{a_first}_{a_last}") or "contact"

        # vCard
        if gen_vcard:
            vcard = build_vcard(a_first, a_last, a_org, a_title, a_phone, a_mobile, a_email, a_website, a_notes)
            # QR for raw vCard (works offline)
            png_img = make_qr_image(vcard, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")

            svg_img = make_qr_image(vcard, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)

            outputs.append({
                "label":"vCard",
                "content": vcard,
                "png": png_buf.getvalue(),
                "svg": svg_buf.getvalue(),
                "filename": f"{base_stub}_vcard"
            })

        # Call
        if gen_call and a_phone.strip():
            tel_url = f"tel:{a_phone.strip()}"
            png_img = make_qr_image(tel_url, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")
            svg_img = make_qr_image(tel_url, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)
            outputs.append({"label":"Call", "content": tel_url, "png": png_buf.getvalue(),
                            "svg": svg_buf.getvalue(), "filename": f"{base_stub}_call"})

        # WhatsApp
        if gen_whatsapp and a_wa.strip():
            wa_url = f"https://wa.me/{a_wa.strip()}"
            png_img = make_qr_image(wa_url, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")
            svg_img = make_qr_image(wa_url, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)
            outputs.append({"label":"WhatsApp", "content": wa_url, "png": png_buf.getvalue(),
                            "svg": svg_buf.getvalue(), "filename": f"{base_stub}_whatsapp"})

        # Email (mailto with optional subject/body)
        if gen_email and a_email.strip():
            params = []
            if a_mail_sub.strip():  params.append("subject=" + a_mail_sub.strip())
            if a_mail_body.strip(): params.append("body=" + a_mail_body.strip())
            mailto = "mailto:" + a_email.strip() + (("?" + "&".join(params)) if params else "")
            png_img = make_qr_image(mailto, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")
            svg_img = make_qr_image(mailto, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)
            outputs.append({"label":"Email", "content": mailto, "png": png_buf.getvalue(),
                            "svg": svg_buf.getvalue(), "filename": f"{base_stub}_email"})

        # Website
        if gen_website and a_website.strip():
            url = a_website.strip()
            png_img = make_qr_image(url, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")
            svg_img = make_qr_image(url, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)
            outputs.append({"label":"Website", "content": url, "png": png_buf.getvalue(),
                            "svg": svg_buf.getvalue(), "filename": f"{base_stub}_website"})

        # SMS
        if gen_sms and a_sms.strip():
            sms_data = f"SMSTO:{a_sms.strip()}:"
            png_img = make_qr_image(sms_data, ec_act, box_act, border_act, as_svg=False,
                                    fg_color=fg_act, bg_color=bg_act, style=style_act)
            png_buf = io.BytesIO(); png_img.save(png_buf, format="PNG")
            svg_img = make_qr_image(sms_data, ec_act, box_act, border_act, as_svg=True)
            svg_buf = io.BytesIO(); svg_img.save(svg_buf)
            outputs.append({"label":"SMS", "content": sms_data, "png": png_buf.getvalue(),
                            "svg": svg_buf.getvalue(), "filename": f"{base_stub}_sms"})

        if not outputs:
            st.info("Select at least one action and fill the relevant fields.")
        else:
            # --- Show gallery & downloads
            st.subheader("QR Gallery")
            cols = st.columns(2)
            for i, item in enumerate(outputs):
                with cols[i % 2]:
                    st.markdown(f"**{item['label']}**")
                    st.image(item["png"], caption=item["content"])
                    st.download_button("⬇️ PNG", data=item["png"],
                                       file_name=f"{item['filename']}.png", mime="image/png",
                                       key=f"act_dl_png_{i}")
                    st.download_button("⬇️ SVG", data=item["svg"],
                                       file_name=f"{item['filename']}.svg", mime="image/svg+xml",
                                       key=f"act_dl_svg_{i}")

            # --- Master ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for item in outputs:
                    zf.writestr(f"{group_name}/{item['filename']}.png", item["png"])
                    zf.writestr(f"{group_name}/{item['filename']}.svg", item["svg"])
                    # add vCard file if present (label == vCard)
                    if item["label"] == "vCard":
                        vcf_name = f"{sanitize_filename(a_first+'_'+a_last) or 'contact'}.vcf"
                        zf.writestr(f"{group_name}/{vcf_name}", vcard_bytes(item["content"]))
                # Summary
                lines = [
                    "Multi-QR Action Export", "-----------------------",
                    f"Folder: {group_name}",
                    f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Actions generated: {len(outputs)}",
                    ""
                ] + [f"- {o['label']}" for o in outputs]
                zf.writestr(f"{group_name}/SUMMARY.txt", "\n".join(lines))
            zip_buf.seek(0)
            st.download_button("📦 Download All (ZIP)", data=zip_buf.getvalue(),
                               file_name=f"{group_name}.zip", mime="application/zip",
                               key="act_dl_zip")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
