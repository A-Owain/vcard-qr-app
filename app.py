# app.py
import io, re, zipfile, base64, textwrap, json
from datetime import datetime
from urllib.parse import urlencode, quote_plus
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import qrcode
from qrcode.image.svg import SvgImage
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

st.set_page_config(page_title="vCard & Multi-QR Generator", page_icon="🔳", layout="centered")

# =========================
# Helpers & core functions
# =========================

def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]", "", s)
    return s or "file"

def build_vcard_core(version, en_first, en_last, org, en_title, phone, mobile, email, website, notes,
                     ar_first=None, ar_last=None, ar_title=None):
    """
    Build vCard 3.0 or 4.0. If Arabic fields provided:
      - vCard 4.0: add FN;LANGUAGE=ar and TITLE;LANGUAGE=ar
      - vCard 3.0: append Arabic into NOTE
    """
    if version == "4.0":
        lines = ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{en_last};{en_first};;;")
        fn_en = f"{en_first} {en_last}".strip()
        lines.append(f"FN:{fn_en}")
        if org:       lines.append(f"ORG:{org}")
        if en_title:  lines.append(f"TITLE:{en_title}")
        if phone:     lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile:    lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email:     lines.append(f"EMAIL:{email}")
        if website:   lines.append(f"URL:{website}")
        # Arabic variants
        if (ar_first or ar_last):
            fn_ar = (" ".join([ar_first or "", ar_last or ""])).strip()
            if fn_ar:
                lines.append(f"FN;LANGUAGE=ar:{fn_ar}")
        if ar_title:
            lines.append(f"TITLE;LANGUAGE=ar:{ar_title}")
        if notes:
            safe = notes.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{safe}")
        lines.append("END:VCARD")
    else:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{en_last};{en_first};;;")
        fn_en = f"{en_first} {en_last}".strip()
        lines.append(f"FN:{fn_en}")
        if org:       lines.append(f"ORG:{org}")
        if en_title:  lines.append(f"TITLE:{en_title}")
        if phone:     lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile:    lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email:     lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website:   lines.append(f"URL:{website}")
        # Arabic fallback into NOTE
        arabic_note = []
        if ar_first or ar_last:
            arabic_note.append(f"الاسم: {(ar_first or '')} {(ar_last or '')}".strip())
        if ar_title:
            arabic_note.append(f"المسمى: {ar_title}")
        if arabic_note:
            lines.append("NOTE:" + " | ".join(arabic_note))
        if notes:
            lines.append("NOTE:" + notes)
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

    # custom dots/rounded for PNG
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

# Simple best-effort parsing for autofill
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{6,}\d)")
URL_RE   = re.compile(r"(https?://[^\s)]+)")

def smart_autofill(text: str):
    out = {
        "first_name": "", "last_name": "", "organization": "",
        "title": "", "phone": "", "mobile": "", "email": "", "website": ""
    }
    if not text:
        return out
    # name guess: first non-empty line, "First Last" or "Last, First"
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        name_line = lines[0]
        if "," in name_line:
            last, first = [p.strip() for p in name_line.split(",", 1)]
            out["first_name"], out["last_name"] = first, last
        else:
            parts = name_line.split()
            if len(parts) >= 2:
                out["first_name"], out["last_name"] = parts[0], parts[-1]
            else:
                out["first_name"] = name_line

    # title/org guess from next lines
    for l in lines[1:4]:
        if not out["title"] and any(k in l.lower() for k in ["manager", "lead", "director", "officer", "engineer", "specialist", "head"]):
            out["title"] = l
        if not out["organization"] and any(k in l.lower() for k in ["company", "inc", "llc", "ltd", "corp", "university", "bank", "agency"]) or len(l.split()) <= 3:
            # heuristic
            out["organization"] = out["organization"] or l

    email = EMAIL_RE.search(text)
    if email: out["email"] = email.group(0)
    urls = URL_RE.findall(text)
    if urls:
        # pick first non-social or the first if all social
        out["website"] = urls[0]
    phones = PHONE_RE.findall(text)
    if phones:
        out["phone"] = phones[0].strip()

    return out

def current_app_url():
    # Best-effort: Streamlit provides query params; base from browser is unknown.
    # Ask user to paste base URL if needed; else relative links work when clicked in app.
    # For QR, we require absolute; let user input base if empty.
    return st.session_state.get("app_base_url", "")

def short_data_uri(b: bytes, mediatype: str, max_len=80_000):
    """Return data URI if under max_len, else None."""
    b64 = base64.b64encode(b).decode("ascii")
    uri = f"data:{mediatype};base64,{b64}"
    return uri if len(uri) <= max_len else None

# -------------
# Styling (light)
# -------------
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
# Landing page renderer
# =========================
query = st.query_params
if query.get("view", [""])[0] == "landing":
    # Render minimal landing page from params
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📇 Contact & Actions")
    name = query.get("name", [""])[0]
    if name:
        st.subheader(name)

    # Buttons/links
    vcf_data = query.get("vcf", [""])[0]   # data:text/vcard... OR https://...
    wa      = query.get("wa", [""])[0]
    site    = query.get("site", [""])[0]
    mailto  = query.get("mailto", [""])[0]
    tel     = query.get("tel", [""])[0]
    audio   = query.get("audio", [""])[0]

    cols = st.columns(2)
    with cols[0]:
        if vcf_data:
            st.link_button("💾 Save Contact", vcf_data, use_container_width=True)
        if site:
            st.link_button("🌐 Website", site, use_container_width=True)
        if mailto:
            st.link_button("✉️ Email", mailto, use_container_width=True)
    with cols[1]:
        if wa:
            st.link_button("💬 WhatsApp", wa, use_container_width=True)
        if tel:
            st.link_button("📞 Call", tel, use_container_width=True)

    if audio:
        st.divider()
        st.subheader("🔊 Audio Greeting")
        # If it's a data URI, embed an HTML5 audio player.
        if audio.startswith("data:audio"):
            st.audio(audio)
        else:
            st.link_button("▶️ Play Audio", audio, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==============================================================
# MAIN APP
# ==============================================================
st.title("🔳 vCard & Multi-QR Generator")
tabs = st.tabs(["Single Mode", "Batch Mode", "Advanced QR", "Multi-QR Landing"])

# ------------------------------
# Sidebar: App base URL (optional)
# ------------------------------
with st.sidebar:
    st.header("App Base URL")
    st.caption("Used to create shareable landing links. Paste your Streamlit app URL once (e.g., https://vcard-qr-app-...streamlit.app)")
    st.session_state.app_base_url = st.text_input("App base URL", value=st.session_state.get("app_base_url", ""), key="base_url")

# ==============================================================
# SINGLE MODE (updated: vCard 3.0/4.0 + Arabic)
# ==============================================================
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Single vCard Generator")

    colA, colB = st.columns(2)
    with colA:
        version     = st.selectbox("vCard Version", ["3.0", "4.0"], index=0, key="s_ver")
        first_name  = st.text_input("First Name", key="s_first")
        phone       = st.text_input("Phone (Work)", "8001249000", key="s_phone")
        email       = st.text_input("Email", key="s_email")
        organization= st.text_input("Organization", key="s_org")
        website     = st.text_input("Website", key="s_web")
    with colB:
        last_name   = st.text_input("Last Name", key="s_last")
        mobile      = st.text_input("Mobile", "+966", key="s_mobile")
        title_en    = st.text_input("Title (English)", key="s_title_en")
        use_ar      = st.checkbox("Add Arabic fields", value=False, key="s_ar_toggle")
        if use_ar:
            ar_first = st.text_input("First Name (Arabic)", key="s_ar_first")
            ar_last  = st.text_input("Last Name (Arabic)", key="s_ar_last")
            ar_title = st.text_input("Title (Arabic)", key="s_ar_title")
        else:
            ar_first = ar_last = ar_title = ""

    notes = st.text_area("Notes", key="s_notes")

    st.subheader("Smart Autofill")
    st.caption("Paste a signature block / profile text (best). Paste URL as plan B (public pages only).")
    autofill_src = st.text_area("Paste text or URL here", key="s_autofill_src", height=100)
    colAF1, colAF2 = st.columns([1,1])
    with colAF1:
        if st.button("Fill from Pasted Text", key="s_af_text"):
            v = smart_autofill(autofill_src)
            st.session_state.s_first  = v["first_name"] or st.session_state.s_first
            st.session_state.s_last   = v["last_name"]  or st.session_state.s_last
            st.session_state.s_org    = v["organization"] or st.session_state.s_org
            st.session_state.s_title_en = v["title"] or st.session_state.s_title_en
            st.session_state.s_phone  = v["phone"] or st.session_state.s_phone
            st.session_state.s_mobile = v["mobile"] or st.session_state.s_mobile
            st.session_state.s_email  = v["email"] or st.session_state.s_email
            st.session_state.s_web    = v["website"] or st.session_state.s_web
            st.success("Autofilled from text (best-effort).")
    with colAF2:
        if st.button("Try Fetch URL (beta)", key="s_af_url"):
            # Best effort fetch of a public URL (may fail on blocked sites).
            try:
                import requests
                r = requests.get(autofill_src, timeout=6)
                txt = r.text
                v = smart_autofill(txt)
                for k, st_key in [
                    ("first_name","s_first"), ("last_name","s_last"),
                    ("organization","s_org"), ("title","s_title_en"),
                    ("phone","s_phone"), ("mobile","s_mobile"),
                    ("email","s_email"), ("website","s_web"),
                ]:
                    st.session_state[st_key] = v[k] or st.session_state.get(st_key, "")
                st.success("Autofilled from URL (best-effort).")
            except Exception as e:
                st.warning(f"Could not fetch URL: {e}")

    st.subheader("QR Settings")
    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="s_ec")
    box_size = st.slider("Box Size", 4, 20, 10, key="s_box")
    border   = st.slider("Border", 2, 10, 4, key="s_border")
    fg_color = st.color_picker("QR Foreground", "#000000", key="s_fg")
    bg_color = st.color_picker("QR Background", "#FFFFFF", key="s_bg")
    style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="s_style")

    if st.button("Generate vCard & QR", use_container_width=True, key="s_btn"):
        vcard = build_vcard_core(version, first_name, last_name, organization, title_en,
                                 phone, mobile, email, website, notes,
                                 ar_first=ar_first, ar_last=ar_last, ar_title=ar_title)
        fname = sanitize_filename(f"{first_name}_{last_name}")

        # vCard download
        st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard),
                           file_name=f"{fname}.vcf", mime="text/vcard",
                           use_container_width=True, key="s_dl_vcf")

        # PNG QR
        img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                            fg_color=fg_color, bg_color=bg_color, style=style)
        png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(png_buf.getvalue(), caption="QR Code")
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download QR (PNG)", data=png_buf.getvalue(),
                           file_name=f"{fname}_qr.png", mime="image/png",
                           use_container_width=True, key="s_dl_png")

        # SVG QR
        svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                fg_color=fg_color, bg_color=bg_color, style=style)
        svg_buf = io.BytesIO(); svg_img.save(svg_buf)
        st.download_button("⬇️ Download QR (SVG)", data=svg_buf.getvalue(),
                           file_name=f"{fname}_qr.svg", mime="image/svg+xml",
                           use_container_width=True, key="s_dl_svg")

        # ZIP bundle
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr(f"{fname}/{fname}.vcf", vcard_bytes(vcard))
            zf.writestr(f"{fname}/{fname}_qr.png", png_buf.getvalue())
            zf.writestr(f"{fname}/{fname}_qr.svg", svg_buf.getvalue())
        zip_buf.seek(0)
        st.download_button("📦 Download All (ZIP)", data=zip_buf.getvalue(),
                           file_name=f"{fname}_bundle.zip", mime="application/zip",
                           use_container_width=True, key="s_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# BATCH MODE (unchanged core, still solid)
# ==============================================================
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Batch Mode (Excel Upload)")
    st.caption("Excel columns: First Name, Last Name, Phone, Mobile, Email, Website, Organization, Title, Notes")

    def generate_excel_template():
        cols = ["First Name", "Last Name", "Phone", "Mobile", "Email", "Website", "Organization", "Title", "Notes"]
        df = pd.DataFrame([{
            "First Name": "Ali", "Last Name": "Saud", "Phone": "8001249000",
            "Mobile": "+966500000000", "Email": "ali@example.com",
            "Website": "https://example.com", "Organization": "Sales Dept",
            "Title": "Manager", "Notes": "VIP Client"
        }], columns=cols)
        buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Template"); buf.seek(0); return buf.getvalue()

    st.download_button("📥 Download Excel Template", data=generate_excel_template(),
                       file_name="batch_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True, key="b_template")

    today_str = datetime.now().strftime("%Y%m%d")
    user_input = st.text_input("Parent folder name for this batch (optional)", key="b_parent")
    batch_folder = (user_input.strip() or "Batch_Contacts") + "_" + today_str

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="b_upload")
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())

        ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3, key="b_ec")
        box_size = st.slider("Box Size", 4, 20, 10, key="b_box")
        border   = st.slider("Border", 2, 10, 4, key="b_border")
        fg_color = st.color_picker("QR Foreground", "#000000", key="b_fg")
        bg_color = st.color_picker("QR Background", "#FFFFFF", key="b_bg")
        style    = st.radio("QR Style", ["square", "dots", "rounded"], index=0, key="b_style")

        if st.button("Generate Batch ZIP", use_container_width=True, key="b_btn"):
            names = []
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    first = str(row.get("First Name", "")).strip()
                    last  = str(row.get("Last Name", "")).strip()
                    fname = sanitize_filename(f"{first}_{last}") or "contact"
                    names.append(f"{first} {last}".strip())

                    vcard = build_vcard_core("3.0", first, last,
                                             str(row.get("Organization", "")),
                                             str(row.get("Title", "")),
                                             str(row.get("Phone", "")),
                                             str(row.get("Mobile", "")),
                                             str(row.get("Email", "")),
                                             str(row.get("Website", "")),
                                             str(row.get("Notes", "")))

                    zf.writestr(f"{batch_folder}/{fname}/{fname}.vcf", vcard_bytes(vcard))

                    img = make_qr_image(vcard, ec_label, box_size, border, as_svg=False,
                                        fg_color=fg_color, bg_color=bg_color, style=style)
                    png_buf = io.BytesIO(); img.save(png_buf, format="PNG")
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.png", png_buf.getvalue())

                    svg_img = make_qr_image(vcard, ec_label, box_size, border, as_svg=True,
                                            fg_color=fg_color, bg_color=bg_color, style=style)
                    svg_buf = io.BytesIO(); svg_img.save(svg_buf)
                    zf.writestr(f"{batch_folder}/{fname}/{fname}_qr.svg", svg_buf.getvalue())

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
                               use_container_width=True, key="b_dl_zip")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# ADVANCED QR (unchanged from your last working state)
# ==============================================================
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Advanced QR Codes")

    # WiFi
    st.subheader("📶 WiFi QR")
    ssid = st.text_input("SSID (Network Name)", key="adv_wifi_ssid")
    password = st.text_input("Password", key="adv_wifi_pass")
    encryption = st.selectbox("Encryption", ["WPA", "WEP", "nopass"], key="adv_wifi_enc")
    if st.button("Generate WiFi QR", key="adv_wifi_btn"):
        wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
        img = make_qr_image(wifi_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="WiFi QR")
        st.download_button("⬇️ WiFi QR PNG", data=buf.getvalue(),
                           file_name="wifi_qr.png", mime="image/png",
                           key="adv_wifi_dl")

    # Event
    st.subheader("📅 Event QR")
    ev_title = st.text_input("Event Title", key="adv_ev_title")
    ev_start = st.text_input("Start (YYYYMMDDTHHMMSSZ)", key="adv_ev_start")
    ev_end   = st.text_input("End (YYYYMMDDTHHMMSSZ)", key="adv_ev_end")
    ev_loc   = st.text_input("Location", key="adv_ev_loc")
    ev_desc  = st.text_area("Description", key="adv_ev_desc")
    if st.button("Generate Event QR", key="adv_ev_btn"):
        event_data = f"BEGIN:VEVENT\nSUMMARY:{ev_title}\nDTSTART:{ev_start}\nDTEND:{ev_end}\nLOCATION:{ev_loc}\nDESCRIPTION:{ev_desc}\nEND:VEVENT"
        img = make_qr_image(event_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Event QR")
        st.download_button("⬇️ Event QR PNG", data=buf.getvalue(),
                           file_name="event_qr.png", mime="image/png",
                           key="adv_ev_dl")

    # MeCard
    st.subheader("🪪 MeCard QR")
    mc_name  = st.text_input("Name (Last,First)", key="adv_mc_name")
    mc_phone = st.text_input("Phone", key="adv_mc_phone")
    mc_email = st.text_input("Email", key="adv_mc_email")
    if st.button("Generate MeCard QR", key="adv_mc_btn"):
        mecard = f"MECARD:N:{mc_name};TEL:{mc_phone};EMAIL:{mc_email};;"
        img = make_qr_image(mecard, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="MeCard QR")
        st.download_button("⬇️ MeCard QR PNG", data=buf.getvalue(),
                           file_name="mecard_qr.png", mime="image/png",
                           key="adv_mc_dl")

    # Crypto
    st.subheader("💰 Crypto Payment QR")
    coin   = st.selectbox("Cryptocurrency", ["bitcoin", "ethereum"], key="adv_cr_coin")
    wallet = st.text_input("Wallet Address", key="adv_cr_wallet")
    amount = st.text_input("Amount (optional)", key="adv_cr_amount")
    if st.button("Generate Crypto QR", key="adv_cr_btn"):
        crypto_data = f"{coin}:{wallet}"
        if amount: crypto_data += f"?amount={amount}"
        img = make_qr_image(crypto_data, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Crypto QR")
        st.download_button("⬇️ Crypto QR PNG", data=buf.getvalue(),
                           file_name="crypto_qr.png", mime="image/png",
                           key="adv_cr_dl")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================
# MULTI-QR LANDING (One QR → many actions + optional audio)
# ==============================================================
with tabs[3]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Multi-QR Landing Page (One QR → Many Actions)")

    st.caption("This creates a QR that opens a mini landing page (inside this app) with buttons like Save Contact, WhatsApp, Website, Email, Call, and optional Audio.")

    # Base for vCard (we’ll produce a data: URL so it’s portable)
    en_first = st.text_input("First Name", key="m_first")
    en_last  = st.text_input("Last Name", key="m_last")
    org      = st.text_input("Organization", key="m_org")
    en_title = st.text_input("Title (English)", key="m_title")
    phone    = st.text_input("Phone (Work)", key="m_phone")
    mobile   = st.text_input("Mobile", key="m_mobile")
    email    = st.text_input("Email", key="m_email")
    website  = st.text_input("Website", key="m_site")
    notes    = st.text_area("Notes", key="m_notes")

    use_ar2  = st.checkbox("Add Arabic fields", value=False, key="m_use_ar")
    if use_ar2:
        ar_first2 = st.text_input("First Name (Arabic)", key="m_ar_first")
        ar_last2  = st.text_input("Last Name (Arabic)", key="m_ar_last")
        ar_title2 = st.text_input("Title (Arabic)", key="m_ar_title")
    else:
        ar_first2 = ar_last2 = ar_title2 = ""

    # Optional extra actions
    wa_num   = st.text_input("WhatsApp number (intl digits, no +)", key="m_wa")
    mailto_to= st.text_input("Email To (mailto)", key="m_mailto")
    tel_num  = st.text_input("Call number (tel:)", key="m_tel")

    # Optional audio greeting
    st.subheader("Optional: Audio Greeting")
    audio_file = st.file_uploader("Upload short MP3/WAV (small files can be inlined)", type=["mp3","wav"], key="m_audio")
    audio_data_uri = ""
    if audio_file is not None:
        raw = audio_file.read()
        # inline up to ~80KB to keep URL & QR size reasonable
        mt = "audio/mpeg" if audio_file.name.lower().endswith(".mp3") else "audio/wav"
        maybe = short_data_uri(raw, mt, max_len=80_000)
        if maybe:
            audio_data_uri = maybe
            st.success("Audio will be embedded on the landing page.")
        else:
            st.warning("Audio too large to inline. It won't be embedded in the landing URL. Include it in your own hosting if needed.")

    # Build vCard (3.0 for max compatibility)
    vcard_landing = build_vcard_core("3.0", en_first, en_last, org, en_title, phone, mobile, email, website, notes,
                                     ar_first=ar_first2, ar_last=ar_last2, ar_title=ar_title2)
    vcard_b64 = base64.b64encode(vcard_landing.replace("\n","\r\n").encode("utf-8")).decode("ascii")
    vcf_data_uri = f"data:text/vcard;charset=utf-8;name={sanitize_filename(en_first+'_'+en_last')}.vcf;base64,{vcard_b64}"

    # Build actions
    wa_url  = f"https://wa.me/{wa_num}" if wa_num.strip() else ""
    site    = website.strip()
    mailto  = f"mailto:{mailto_to.strip()}" if mailto_to.strip() else ""
    tel     = f"tel:{tel_num.strip()}" if tel_num.strip() else ""

    # Landing link
    base = current_app_url().rstrip("/")
    if not base:
        st.info("Tip: set your Streamlit base URL in the sidebar so the QR opens the landing page from anywhere.")
    params = {
        "view": "landing",
        "name": f"{en_first} {en_last}".strip(),
        "vcf": vcf_data_uri,
    }
    if wa_url:  params["wa"] = wa_url
    if site:    params["site"] = site
    if mailto:  params["mailto"] = mailto
    if tel:     params["tel"] = tel
    if audio_data_uri: params["audio"] = audio_data_uri

    landing_url = (base + "?" + urlencode(params, quote_via=quote_plus)) if base else ("?" + urlencode(params, quote_via=quote_plus))
    st.text_input("Landing Page URL", value=landing_url, key="m_link")

    # Generate QR for landing
    st.subheader("Landing QR Settings")
    ec_label2 = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=2, key="m_ec")
    box2      = st.slider("Box Size", 4, 20, 10, key="m_box")
    border2   = st.slider("Border", 2, 10, 4, key="m_border")
    style2    = st.radio("QR Style", ["square","dots","rounded"], index=0, key="m_style")
    fg2       = st.color_picker("QR Foreground", "#000000", key="m_fg")
    bg2       = st.color_picker("QR Background", "#FFFFFF", key="m_bg")

    if st.button("Generate Landing QR", key="m_btn"):
        img2 = make_qr_image(landing_url, ec_label2, box2, border2, as_svg=False,
                             fg_color=fg2, bg_color=bg2, style=style2)
        buf2 = io.BytesIO(); img2.save(buf2, format="PNG")
        st.markdown('<div class="qr-preview">', unsafe_allow_html=True)
        st.image(buf2.getvalue(), caption="Landing QR")
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download Landing QR (PNG)", data=buf2.getvalue(),
                           file_name=f"{sanitize_filename(en_first+'_'+en_last)}_landing_qr.png",
                           mime="image/png", key="m_dl_png")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("""
---
<p style="text-align: center; font-size: 0.9em; color:#888;">
Developed by Abdulrrahman Alowain • <a href="https://x.com/a_owain" target="_blank">Follow Me</a>
</p>
""", unsafe_allow_html=True)
