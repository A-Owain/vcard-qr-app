# app.py
import io, re, base64
from datetime import datetime
from urllib.parse import quote_plus
import streamlit as st
from PIL import Image
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

def build_vcard(
    version: str,
    first_name: str = "",
    last_name: str = "",
    organization: str = "",
    title: str = "",
    phone: str = "",
    mobile: str = "",
    email: str = "",
    website: str = "",
    notes: str = "",
    photo_mode: str = "none",           # "none" | "embed"
    photo_mediatype: str = "",
    photo_b64: str = "",
) -> str:
    """Return a vCard 3.0/4.0 WITHOUT address/timezone. Supports embedded PHOTO."""
    lines = []
    if version == "3.0":
        lines += ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization.strip(): lines.append(f"ORG:{organization}")
        if title.strip():         lines.append(f"TITLE:{title}")
        if phone.strip():         lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if mobile.strip():        lines.append(f"TEL;TYPE=CELL,VOICE:{mobile}")
        if email.strip():         lines.append(f"EMAIL;TYPE=PREF,INTERNET:{email}")
        if website.strip():       lines.append(f"URL:{website}")
        if photo_mode == "embed" and photo_b64 and photo_mediatype:
            img_type = photo_mediatype.split("/")[-1].upper()
            lines.append(f"PHOTO;TYPE={img_type};ENCODING=b:{photo_b64}")
        if notes.strip():
            safe_notes = notes.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{safe_notes}")
        lines.append("END:VCARD")
    else:
        lines += ["BEGIN:VCARD", "VERSION:4.0"]
        lines.append(f"N:{last_name};{first_name};;;")
        fn = (first_name + " " + last_name).strip()
        lines.append(f"FN:{fn}")
        if organization.strip(): lines.append(f"ORG:{organization}")
        if title.strip():         lines.append(f"TITLE:{title}")
        if phone.strip():         lines.append(f"TEL;TYPE=work,voice;VALUE=uri:tel:{phone}")
        if mobile.strip():        lines.append(f"TEL;TYPE=cell,voice;VALUE=uri:tel:{mobile}")
        if email.strip():         lines.append(f"EMAIL:{email}")
        if website.strip():       lines.append(f"URL:{website}")
        if photo_mode == "embed" and photo_b64 and photo_mediatype:
            lines.append(f"PHOTO:data:{photo_mediatype};base64,{photo_b64}")
        if notes.strip():
            safe_notes = notes.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{safe_notes}")
        lines.append("END:VCARD")
    return "\n".join(lines)

def vcard_bytes(vcard_str: str) -> bytes:
    return vcard_str.replace("\n", "\r\n").encode("utf-8")

def vcard_data_uri(vcard_str: str, name: str) -> str:
    b = vcard_bytes(vcard_str)
    b64 = base64.b64encode(b).decode("ascii")
    return f"data:text/vcard;charset=utf-8;name={name}.vcf;base64,{b64}"

EC_LEVELS = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}

def make_qr_image(data: str, ec_label: str, box_size: int, border: int, as_svg: bool):
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
    return qr.make_image(fill_color="black", back_color="white")

def try_make_qr(content: str, ec_label: str, box_size: int, border: int, as_svg: bool):
    try:
        return make_qr_image(content, ec_label, box_size, border, as_svg), None
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

def guess_mediatype(filename: str) -> str:
    f = filename.lower()
    if f.endswith((".jpg", ".jpeg")): return "image/jpeg"
    if f.endswith(".png"):            return "image/png"
    return "application/octet-stream"

# ---------- UI: Global settings ----------
st.title("🔳 vCard & Multi-QR Generator")
st.caption("vCard + WhatsApp + Website + Email + Phone • PNG/SVG • Permanent data: links • Optional photo")

with st.sidebar:
    st.header("QR Settings")
#    version = st.selectbox("vCard Version", ["3.0", "4.0"], index=0)
#    ec_label = st.selectbox("Error Correction", list(EC_LEVELS.keys()), index=3)
#    box_size = st.slider("Box Size (px per module)", 4, 20, 10)
#    border   = st.slider("Border (modules)", 2, 10, 4)
    fmt      = st.radio("QR Output Format", ["PNG", "SVG"], index=0)
    with_logo = st.checkbox("Add center logo (PNG/JPG)", value=False)
    logo_scale = st.slider("Logo relative size", 0.10, 0.35, 0.22, 0.01, disabled=not with_logo)
    logo_bytes = None
    if with_logo:
        logo_file = st.file_uploader("Upload logo", type=["png", "jpg", "jpeg"])
        if logo_file: logo_bytes = logo_file.read()

# ---------- vCard builder ----------
st.header("vCard")
c1, c2 = st.columns(2)
with c1:
    first_name = st.text_input("First Name / الاسم الأول")
    phone      = st.text_input("Phone (Work) / هاتف العمل", value="8001249000")
    email      = st.text_input("Email / البريد الإلكتروني")
with c2:
    last_name  = st.text_input("Last Name / اسم العائلة")
    mobile     = st.text_input("Mobile / الجوال")
    website    = st.text_input("Website / الموقع", value="https://alraedah.sa")

organization = st.text_input("Organization / الشركة", value="Alraedah Finance")
title        = st.text_input("Title / المسمى الوظيفي")
notes        = st.text_area("Notes / ملاحظات (اختياري)", height=100)

# Optional profile photo
st.subheader("Profile Photo (Optional)")
add_photo = st.checkbox("Attach a profile photo")
photo_mode = "none"; photo_mediatype=""; photo_b64=""
if add_photo:
    photo_file = st.file_uploader("Upload headshot (JPG/PNG)", type=["jpg", "jpeg", "png"])
    if photo_file is not None:
        _bytes = photo_file.read()
        photo_mediatype = guess_mediatype(photo_file.name)
        photo_mode = "embed"
        photo_b64 = base64.b64encode(_bytes).decode("ascii")

# Filenames
display_name = (first_name + " " + last_name).strip() or "contact"
base_name    = (first_name + "_" + last_name).strip("_") or "contact"
timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")

# Build vCard
vcard = build_vcard(
    version=version,
    first_name=first_name,
    last_name=last_name,
    organization=organization,
    title=title,
    phone=phone,
    mobile=mobile,
    email=email,
    website=website,
    notes=notes,
    photo_mode=photo_mode if add_photo else "none",
    photo_mediatype=photo_mediatype,
    photo_b64=photo_b64,
)

vcf_fname = f"{base_name}_vcard_{timestamp}.vcf"
data_uri  = vcard_data_uri(vcard, base_name)

st.subheader("vCard Preview")
st.code(vcard, language="text")
st.download_button("💳 Download vCard (.vcf)", data=vcard_bytes(vcard), file_name=vcf_fname, mime="text/vcard")
st.text_input("Shareable vCard link (permanent)", value=data_uri)

# ---------- MULTI-QR: build QR contents ----------
st.header("Multi-QR Contents")
with st.expander("WhatsApp"):
    wa_num = st.text_input("WhatsApp number (intl digits only)", placeholder="9665XXXXXXXX")
    wa_msg = st.text_input("Prefilled message (optional)")
with st.expander("Website"):
    web_url = st.text_input("Website URL", value="https://alraedah.sa")
with st.expander("Email (mailto:)"):
    mail_to   = st.text_input("To", placeholder="name@example.com")
    mail_sub  = st.text_input("Subject")
    mail_body = st.text_area("Body", height=80)
with st.expander("Phone (tel:)"):
    tel_num = st.text_input("Phone number", placeholder="+966XXXXXXXXX")

# Choice for vCard QR
st.subheader("vCard QR Content")
qr_choice = st.radio("vCard QR should encode:", ["Raw vCard text", "Permanent data URI"], index=0)
force_link_if_big = st.checkbox("Auto-use Data URI if QR too dense", value=True)

# Assemble QR items
items = []
items.append({
    "label": f"vCard ({display_name or 'contact'})",
    "content": vcard if qr_choice == "Raw vCard text" else data_uri,
    "filename_stub": f"{base_name}_vcard_{timestamp}"
})
if wa_num:
    url = f"https://wa.me/{wa_num}"
    if wa_msg: url += f"?text={quote_plus(wa_msg)}"
    items.append({"label": "WhatsApp", "content": url, "filename_stub": f"{base_name}_whatsapp_{timestamp}"})
if web_url:
    items.append({"label": "Website", "content": web_url, "filename_stub": f"{base_name}_website_{timestamp}"})
if mail_to:
    params = []
    if mail_sub:  params.append("subject=" + quote_plus(mail_sub))
    if mail_body: params.append("body=" + quote_plus(mail_body))
    url = f"mailto:{mail_to}" + (("?" + "&".join(params)) if params else "")
    items.append({"label": "Email", "content": url, "filename_stub": f"{base_name}_email_{timestamp}"})
if tel_num:
    items.append({"label": "Phone", "content": f"tel:{tel_num}", "filename_stub": f"{base_name}_phone_{timestamp}"})

# ---------- Render QR gallery ----------
st.subheader("QR Gallery")
if not items:
    st.info("Add at least one item above to generate QR codes.")
else:
    cols = st.columns(2)
    for idx, item in enumerate(items):
        label = item["label"]; content = item["content"]; stub = item["filename_stub"]
        img, err = try_make_qr(content, ec_label, box_size, border, as_svg=(fmt=="SVG"))
        if err == "oversize" and label.startswith("vCard") and force_link_if_big:
            st.warning("vCard QR too dense. Switched to data URI.")
            content = data_uri
            img, _ = try_make_qr(content, ec_label, box_size, border, as_svg=(fmt=="SVG"))
        with cols[idx % 2]:
            st.markdown(f"**{label}**")
            if fmt == "SVG":
                if img:
                    b = io.BytesIO(); img.save(b)
                    st.markdown(b.getvalue().decode("utf-8"), unsafe_allow_html=True)
                    st.download_button("⬇️ Download SVG", data=b.getvalue(), file_name=f"{stub}.svg", mime="image/svg+xml")
            else:
                if img:
                    pil = img.convert("RGB")
                    if with_logo and logo_bytes:
                        try: pil = overlay_logo(pil, logo_bytes, scale=logo_scale)
                        except Exception as e: st.warning(f"Logo overlay failed: {e}")
                    b = io.BytesIO(); pil.save(b, format="PNG")
                    st.image(b.getvalue())
                    st.download_button("⬇️ Download PNG", data=b.getvalue(), file_name=f"{stub}.png", mime="image/png")

st.markdown("---")
st.caption("Made with ❤️ by Abdurrahman Alowain.")