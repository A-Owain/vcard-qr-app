import streamlit as st
import qrcode
from qrcode.image.svg import SvgImage
import pandas as pd
from io import BytesIO
from PIL import Image
import zipfile
import base64

import barcode
from barcode.writer import ImageWriter

# -------------------------
# QR Code Generator (Basic)
# -------------------------
def qr_generator_tab():
    st.header("🔲 QR Code Generator")

    data = st.text_area("Enter text or URL to encode")
    if st.button("Generate QR Code"):
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_Q
        )
        qr.add_data(data)
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

        # Display
        st.image(png_data, caption="Generated QR Code", use_column_width=True)

        # Downloads
        st.download_button("⬇️ Download PNG", png_data, "qr_code.png", "image/png")
        st.download_button("⬇️ Download SVG", svg_data, "qr_code.svg", "image/svg+xml")

        # ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("qr_code.png", png_data)
            zipf.writestr("qr_code.svg", svg_data)

        st.download_button(
            "⬇️ Download All (ZIP)",
            zip_buffer.getvalue(),
            "qr_package.zip",
            "application/zip"
        )


# -------------------------
# Batch QR Code Generator
# -------------------------
def batch_qr_tab():
    st.header("📑 Batch QR Code Generator")

    uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)

        if st.button("Generate Batch QR Codes"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for _, row in df.iterrows():
                    text = str(row[0])
                    qr = qrcode.QRCode(
                        error_correction=qrcode.constants.ERROR_CORRECT_Q
                    )
                    qr.add_data(text)
                    qr.make(fit=True)

                    # PNG
                    img_png = qr.make_image(fill_color="black", back_color="white")
                    buf_png = BytesIO()
                    img_png.save(buf_png, format="PNG")

                    # SVG
                    img_svg = qr.make_image(image_factory=SvgImage)
                    buf_svg = BytesIO()
                    img_svg.save(buf_svg)

                    # Save files
                    zipf.writestr(f"{text}.png", buf_png.getvalue())
                    zipf.writestr(f"{text}.svg", buf_svg.getvalue())

            st.download_button(
                "⬇️ Download All as ZIP",
                zip_buffer.getvalue(),
                "batch_qr_codes.zip",
                "application/zip"
            )


# -------------------------
# vCard QR Code Generator
# -------------------------
def vcard_tab():
    st.header("📇 vCard QR Code Generator")

    # Inputs
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    company = st.text_input("Company")
    job_title = st.text_input("Job Title")
    website = st.text_input("Website")

    # Profile picture
    photo_file = st.file_uploader("Upload Profile Picture (optional)", type=["jpg", "jpeg", "png"])
    photo_base64 = None
    if photo_file:
        img = Image.open(photo_file).convert("RGB")
        img.thumbnail((150, 150))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        photo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # vCard content
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

    # Generate QR
    if st.button("Generate vCard QR"):
        qr = qrcode.QRCode(
            version=40,  # FIX: allow largest size for photo embedding
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=10,
            border=4
        )
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

        # Display
        st.image(png_data, caption="Your vCard QR", use_column_width=True)

        # Downloads
        st.download_button("⬇️ Download PNG", png_data, "vcard_qr.png", "image/png")
        st.download_button("⬇️ Download SVG", svg_data, "vcard_qr.svg", "image/svg+xml")
        st.download_button("⬇️ Download VCF", vcf_data, "contact.vcf", "text/vcard")

        # ZIP
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


# -------------------------
# Product Barcode Generator
# -------------------------
def barcode_tab():
    st.header("🏷️ Product Barcode Generator")

    data = st.text_input("Enter product code")
    barcode_type = st.selectbox("Select Barcode Type", ["code128", "ean13", "upc"])

    if st.button("Generate Barcode"):
        try:
            barcode_class = barcode.get_barcode_class(barcode_type)
            bar = barcode_class(data, writer=ImageWriter())

            # PNG
            buf_png = BytesIO()
            bar.write(buf_png, options={"write_text": False})
            png_data = buf_png.getvalue()

            # Display
            st.image(png_data, caption="Generated Barcode", use_column_width=True)

            # Downloads
            st.download_button("⬇️ Download PNG", png_data, "barcode.png", "image/png")

            # ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                zipf.writestr("barcode.png", png_data)

            st.download_button(
                "⬇️ Download All (ZIP)",
                zip_buffer.getvalue(),
                "barcode_package.zip",
                "application/zip"
            )
        except Exception as e:
            st.error(f"Error: {e}")


# -------------------------
# Main App
# -------------------------
def main():
    st.set_page_config(page_title="QR & Barcode Tools", layout="centered")
    tabs = ["QR Generator", "Batch QR", "vCard QR", "Barcode Generator"]
    choice = st.tabs(tabs)

    with choice[0]:
        qr_generator_tab()
    with choice[1]:
        batch_qr_tab()
    with choice[2]:
        vcard_tab()
    with choice[3]:
        barcode_tab()


if __name__ == "__main__":
    main()
