import streamlit as st
import qrcode
from qrcode.image.svg import SvgImage
from PIL import Image
from io import BytesIO
import pandas as pd
import base64
import zipfile
import barcode
from barcode.writer import ImageWriter


# ---------------- Normal QR Tab ----------------
def normal_qr_tab():
    st.header("🔲 Normal QR Code Generator")

    data = st.text_area("Enter text or URL")
    if st.button("Generate QR Code"):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q)
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

        st.image(png_data, caption="Your QR Code", use_column_width=True)
        st.download_button("⬇️ Download PNG", png_data, "qr_code.png", "image/png")
        st.download_button("⬇️ Download SVG", svg_data, "qr_code.svg", "image/svg+xml")


# ---------------- Batch vCard QR Tab ----------------
def batch_qr_tab():
    st.header("📂 Batch vCard QR Code Generator")

    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Preview:", df.head())

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for _, row in df.iterrows():
                first, last = str(row.get("FirstName", "")), str(row.get("LastName", ""))
                phone, email = str(row.get("Phone", "")), str(row.get("Email", ""))
                company, job, website = str(row.get("Company", "")), str(row.get("JobTitle", "")), str(row.get("Website", ""))

                vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last};{first};;;
FN:{first} {last}
ORG:{company}
TITLE:{job}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
URL:{website}
END:VCARD"""

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

                base_name = f"{first}_{last}".strip("_")
                zipf.writestr(f"{base_name}/{base_name}.png", png_data)
                zipf.writestr(f"{base_name}/{base_name}.svg", svg_data)
                zipf.writestr(f"{base_name}/{base_name}.vcf", vcf_data)

        st.download_button(
            "⬇️ Download All vCards (ZIP)",
            zip_buffer.getvalue(),
            "Batch_QR_vCards.zip",
            "application/zip"
        )


# ---------------- Single vCard QR Tab ----------------
def vcard_tab():
    st.header("📇 vCard QR Code Generator")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    company = st.text_input("Company")
    job_title = st.text_input("Job Title")
    website = st.text_input("Website")

    photo_file = st.file_uploader("Upload Profile Picture (optional)", type=["jpg", "jpeg", "png"])
    photo_base64 = None
    if photo_file:
        img = Image.open(photo_file).convert("RGB")
        img.thumbnail((150, 150))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        photo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

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

        st.image(png_data, caption="Your vCard QR", use_column_width=True)

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


# ---------------- Product Barcode Tab ----------------
def barcode_tab():
    st.header("🏷️ Product Barcode Generator")

    barcode_type = st.selectbox("Choose barcode type", ["code128", "ean13", "upc"])
    product_code = st.text_input("Enter product code")

    if st.button("Generate Barcode"):
        try:
            BARCODE = barcode.get_barcode_class(barcode_type)
            bar = BARCODE(product_code, writer=ImageWriter())

            buf_png = BytesIO()
            bar.write(buf_png, options={"write_text": False})
            png_data = buf_png.getvalue()

            st.image(png_data, caption="Your Barcode", use_column_width=True)
            st.download_button("⬇️ Download Barcode (PNG)", png_data, "barcode.png", "image/png")

        except Exception as e:
            st.error(f"Error: {e}")


# ---------------- Main App ----------------
def main():
    st.title("🧰 QR & Barcode Toolkit")

    tab1, tab2, tab3, tab4 = st.tabs(["Normal QR", "Batch vCard QR", "vCard QR", "Product Barcode"])

    with tab1:
        normal_qr_tab()
    with tab2:
        batch_qr_tab()
    with tab3:
        vcard_tab()
    with tab4:
        barcode_tab()


if __name__ == "__main__":
    main()
# ---------------- End of File ----------------