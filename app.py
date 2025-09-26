import streamlit as st
import qrcode
from qrcode.image.svg import SvgImage
import base64
from io import BytesIO
from PIL import Image
import zipfile

def vcard_tab():
    st.header("📇 vCard QR Code Generator")

    # --- Input fields ---
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    company = st.text_input("Company")
    job_title = st.text_input("Job Title")
    website = st.text_input("Website")

    # --- Profile picture upload ---
    photo_file = st.file_uploader("Upload Profile Picture (optional)", type=["jpg", "jpeg", "png"])
    photo_base64 = None
    if photo_file:
        img = Image.open(photo_file).convert("RGB")
        img.thumbnail((150, 150))  # resize small to keep QR scannable
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        photo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # --- Generate vCard content ---
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{company}
TITLE:{job_title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
URL:{website}
"""

    if photo_base64:
        vcard += f"PHOTO;ENCODING=b;TYPE=JPEG:{photo_base64}\n"

    vcard += "END:VCARD"

    # --- Generate QR ---
    if st.button("Generate vCard QR"):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q)
        qr.add_data(vcard)
        qr.make(fit=True)

        # PNG
        img_png = qr.make_image(fill_color="black", back_color="white")
        buf_png = BytesIO()
        img_png.save(buf_png, format="PNG")
        png_data = buf_png.getvalue()

        # SVG
        img_svg = qr.make_image(image_factory=SvgImage)
        buf_svg = BytesIO()
        img_svg.save(buf_svg)
        svg_data = buf_svg.getvalue()

        # VCF
        vcf_data = vcard.encode("utf-8")

        # --- Display ---
        st.image(png_data, caption="Your vCard QR", use_column_width=True)

        # --- Individual Downloads ---
        st.download_button("⬇️ Download PNG", png_data, "vcard_qr.png", "image/png")
        st.download_button("⬇️ Download SVG", svg_data, "vcard_qr.svg", "image/svg+xml")
        st.download_button("⬇️ Download VCF", vcf_data, "contact.vcf", "text/vcard")

        # --- ZIP file with all formats ---
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("vcard_qr.png", png_data)
            zipf.writestr("vcard_qr.svg", svg_data)
            zipf.writestr("contact.vcf", vcf_data)

        st.download_button(
            "⬇️ Download All (ZIP)",
            zip_buffer.getvalue(),
            "vcard_package.zip",
            "application/zip"
        )
