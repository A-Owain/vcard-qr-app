import streamlit as st
import qrcode
import pandas as pd
import zipfile
import io
import os
from PIL import Image
import barcode
from barcode.writer import ImageWriter
from pyzbar.pyzbar import decode

# -----------------------
# Utility Functions
# -----------------------
def create_vcard(first_name, last_name, phone, email, company, job_title, website):
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{company}
TITLE:{job_title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
URL:{website}
END:VCARD"""
    return vcard

def generate_qr_code(data, file_type="PNG"):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format=file_type)
    buf.seek(0)
    return buf

def generate_barcode(data, barcode_type="code128", file_type="PNG"):
    BARCODE_CLASSES = {
        "Code128": barcode.get_barcode_class("code128"),
        "EAN13": barcode.get_barcode_class("ean13"),
        "UPC": barcode.get_barcode_class("upc"),
    }
    BarcodeClass = BARCODE_CLASSES[barcode_type]
    code = BarcodeClass(data, writer=ImageWriter())
    buf = io.BytesIO()
    code.write(buf, options={"format": file_type.lower()})
    buf.seek(0)
    return buf

def save_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for filename, filecontent in files_dict.items():
            zf.writestr(filename, filecontent.getvalue())
    buf.seek(0)
    return buf

# -----------------------
# Streamlit Tabs
# -----------------------
st.title("🔗 QR & Barcode Generator + Scanner")

tab1, tab2, tab3, tab4 = st.tabs([
    "📇 vCard QR Generator",
    "📂 Batch QR Generator",
    "📦 Product Barcode Generator",
    "📷 QR / Barcode Scanner"
])

# -----------------------
# Tab 1: vCard QR Generator
# -----------------------
with tab1:
    st.header("📇 vCard QR Generator")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    company = st.text_input("Company")
    job_title = st.text_input("Job Title")
    website = st.text_input("Website")

    if st.button("Generate vCard QR"):
        vcard = create_vcard(first_name, last_name, phone, email, company, job_title, website)

        qr_png = generate_qr_code(vcard, "PNG")
        qr_svg = generate_qr_code(vcard, "SVG")
        vcf_file = io.BytesIO(vcard.encode("utf-8"))

        st.image(qr_png, caption="Generated vCard QR")

        # Download buttons
        st.download_button("Download PNG", qr_png, file_name="vcard.png", mime="image/png")
        st.download_button("Download SVG", qr_svg, file_name="vcard.svg", mime="image/svg+xml")
        st.download_button("Download VCF", vcf_file, file_name="vcard.vcf", mime="text/vcard")

        # ZIP download
        files = {"vcard.png": qr_png, "vcard.svg": qr_svg, "vcard.vcf": vcf_file}
        zip_buf = save_zip(files)
        st.download_button("Download All (ZIP)", zip_buf, file_name="vcard_qr.zip", mime="application/zip")

# -----------------------
# Tab 2: Batch QR Generator
# -----------------------
with tab2:
    st.header("📂 Batch QR Generator")
    uploaded_file = st.file_uploader("Upload Excel file with contacts", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Preview of uploaded data:", df.head())

        if st.button("Generate Batch QR"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for _, row in df.iterrows():
                    vcard = create_vcard(
                        row.get("First Name", ""),
                        row.get("Last Name", ""),
                        row.get("Phone", ""),
                        row.get("Email", ""),
                        row.get("Company", ""),
                        row.get("Job Title", ""),
                        row.get("Website", ""),
                    )

                    qr_png = generate_qr_code(vcard, "PNG")
                    qr_svg = generate_qr_code(vcard, "SVG")
                    vcf_file = io.BytesIO(vcard.encode("utf-8"))

                    base_name = f"{row.get('First Name','')}_{row.get('Last Name','')}"
                    zf.writestr(f"{base_name}.png", qr_png.getvalue())
                    zf.writestr(f"{base_name}.svg", qr_svg.getvalue())
                    zf.writestr(f"{base_name}.vcf", vcf_file.getvalue())

            zip_buf.seek(0)
            st.download_button("Download All (ZIP)", zip_buf, file_name="batch_qr_vcards.zip", mime="application/zip")

# -----------------------
# Tab 3: Product Barcode Generator
# -----------------------
with tab3:
    st.header("📦 Product Barcode Generator")
    data = st.text_input("Enter product code or number")
    barcode_type = st.selectbox("Select Barcode Type", ["Code128", "EAN13", "UPC"])

    if st.button("Generate Barcode"):
        try:
            barcode_png = generate_barcode(data, barcode_type, "PNG")
            barcode_svg = generate_barcode(data, barcode_type, "SVG")

            st.image(barcode_png, caption=f"Generated {barcode_type} Barcode")

            # Download buttons
            st.download_button("Download PNG", barcode_png, file_name=f"{barcode_type}.png", mime="image/png")
            st.download_button("Download SVG", barcode_svg, file_name=f"{barcode_type}.svg", mime="image/svg+xml")

            # ZIP download
            files = {f"{barcode_type}.png": barcode_png, f"{barcode_type}.svg": barcode_svg}
            zip_buf = save_zip(files)
            st.download_button("Download All (ZIP)", zip_buf, file_name=f"{barcode_type}_barcode.zip", mime="application/zip")

        except Exception as e:
            st.error(f"Error: {e}")

# -----------------------
# Tab 4: QR / Barcode Scanner
# -----------------------
with tab4:
    st.header("📷 QR / Barcode Scanner")
    uploaded_file = st.file_uploader("Upload an image with QR or Barcode", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_column_width=True)

        decoded_objects = decode(img)

        if decoded_objects:
            st.subheader("🔍 Decoded Data")
            decoded_texts = []
            for obj in decoded_objects:
                decoded_data = obj.data.decode("utf-8")
                decoded_texts.append(decoded_data)
                st.write(f"**Type:** {obj.type}")
                st.write(f"**Data:** {decoded_data}")
                st.markdown("---")

            decoded_text = "\n".join(decoded_texts)
            st.download_button(
                label="💾 Download Decoded Data (.txt)",
                data=decoded_text,
                file_name="decoded_data.txt",
                mime="text/plain"
            )
        else:
            st.error("No QR or Barcode detected in the image.")
