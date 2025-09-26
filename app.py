import streamlit as st
import qrcode
import io
import zipfile
import pandas as pd
from PIL import Image
import treepoem  # For barcode generation
import base64
import os

# -----------------------
# Helper functions
# -----------------------

def generate_qr_code(data, fmt="PNG"):
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    if fmt == "SVG":
        qr_img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        qr_img.save(buf)
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()


def create_vcard(first, last, phone, email, company, job, website, dept="", location=""):
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last};{first};;;
FN:{first} {last}
ORG:{company}
TITLE:{job}
TEL;TYPE=CELL:{phone}
EMAIL;TYPE=INTERNET:{email}
URL:{website}
"""
    if dept:
        vcard += f"DEPARTMENT:{dept}\n"
    if location:
        vcard += f"ADR;TYPE=WORK:{location}\n"

    vcard += "END:VCARD"
    return vcard


def download_link(data, filename, mime):
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}">⬇️ Download {filename}</a>'
    return href


# -----------------------
# Streamlit UI
# -----------------------

st.set_page_config(page_title="QR & Barcode Generator", layout="wide")
st.title("✨ QR & Barcode Generator Suite")

tabs = st.tabs([
    "🔹 Single QR",
    "📑 Batch QR",
    "👤 vCard QR",
    "👥 Batch vCard QR",
    "🏷 Product Barcode",
    "🏢 Employee Directory"
])

# -----------------------
# Single QR
# -----------------------
with tabs[0]:
    st.header("🔹 Single QR Generator")
    text = st.text_input("Enter text or URL")
    if st.button("Generate QR", key="single_qr"):
        if text:
            png = generate_qr_code(text, "PNG")
            svg = generate_qr_code(text, "SVG")
            st.image(png, caption="Generated QR", use_column_width=True)
            st.download_button("⬇️ Download PNG", png, "qr.png", "image/png")
            st.download_button("⬇️ Download SVG", svg, "qr.svg", "image/svg+xml")

# -----------------------
# Batch QR
# -----------------------
with tabs[1]:
    st.header("📑 Batch QR Generator")
    uploaded = st.file_uploader("Upload CSV with 'data' column", type=["csv"], key="batch_qr")
    if uploaded:
        df = pd.read_csv(uploaded)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                data = str(row["data"])
                png = generate_qr_code(data, "PNG")
                svg = generate_qr_code(data, "SVG")
                zf.writestr(f"{data}.png", png)
                zf.writestr(f"{data}.svg", svg)
        st.download_button("⬇️ Download All (ZIP)", zip_buf.getvalue(), "batch_qr.zip", "application/zip")

# -----------------------
# vCard QR
# -----------------------
with tabs[2]:
    st.header("👤 vCard QR Generator")
    col1, col2 = st.columns(2)
    with col1:
        first = st.text_input("First Name")
        last = st.text_input("Last Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
    with col2:
        company = st.text_input("Company")
        job = st.text_input("Job Title")
        website = st.text_input("Website")
    dept = st.text_input("Department (optional)")
    location = st.text_input("Location (optional)")

    if st.button("Generate vCard QR"):
        vcard = create_vcard(first, last, phone, email, company, job, website, dept, location)
        png = generate_qr_code(vcard, "PNG")
        svg = generate_qr_code(vcard, "SVG")
        st.image(png, caption="vCard QR", use_column_width=True)
        st.download_button("⬇️ Download PNG", png, f"{first}_{last}.png", "image/png")
        st.download_button("⬇️ Download SVG", svg, f"{first}_{last}.svg", "image/svg+xml")
        st.download_button("⬇️ Download vCard", vcard.encode(), f"{first}_{last}.vcf", "text/vcard")

# -----------------------
# Batch vCard QR
# -----------------------
with tabs[3]:
    st.header("👥 Batch vCard QR Generator")
    uploaded = st.file_uploader("Upload Excel with employee info", type=["xlsx"], key="batch_vcard")

    if uploaded:
        df = pd.read_excel(uploaded)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                first, last = row["First Name"], row["Last Name"]
                phone, email = row["Phone"], row["Email"]
                company, job, website = row["Company"], row["Job Title"], row["Website"]
                dept, location = row.get("Department", ""), row.get("Location", "")
                vcard = create_vcard(first, last, phone, email, company, job, website, dept, location)

                folder = f"{first}_{last}"
                png = generate_qr_code(vcard, "PNG")
                svg = generate_qr_code(vcard, "SVG")

                zf.writestr(f"{folder}/{folder}.vcf", vcard)
                zf.writestr(f"{folder}/{folder}.png", png)
                zf.writestr(f"{folder}/{folder}.svg", svg)

        st.download_button("⬇️ Download All (ZIP)", zip_buf.getvalue(), "batch_vcards.zip", "application/zip")

# -----------------------
# Product Barcode
# -----------------------
with tabs[4]:
    st.header("🏷 Product Barcode")
    code_text = st.text_input("Enter product code or text")
    barcode_type = st.selectbox("Barcode Format", ["code128", "ean13", "upca"])

    if st.button("Generate Barcode"):
        if not code_text.strip():
            st.warning("Please enter text")
        else:
            try:
                img = treepoem.generate_barcode(
                    barcode_type=barcode_type,
                    data=code_text,
                )
                png_buf = io.BytesIO()
                img.convert("1").save(png_buf, "PNG")
                png_bytes = png_buf.getvalue()
                st.image(png_bytes, caption="Generated Barcode")
                st.download_button("⬇️ Download PNG", png_bytes, f"{code_text}.png", "image/png")
            except Exception as e:
                st.error(f"Error: {e}")

# -----------------------
# Employee Directory
# -----------------------
with tabs[5]:
    st.header("🏢 Employee Directory")

    # Download template
    if st.button("⬇️ Download Excel Template"):
        template = pd.DataFrame(columns=[
            "First Name", "Last Name", "Phone", "Email", "Company",
            "Job Title", "Website", "Department", "Location"
        ])
        buf = io.BytesIO()
        template.to_excel(buf, index=False)
        st.download_button("Download Template.xlsx", buf.getvalue(), "employee_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    uploaded = st.file_uploader("Upload filled Excel template", type=["xlsx"], key="employee_directory")

    if uploaded:
        df = pd.read_excel(uploaded)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for _, row in df.iterrows():
                first, last = row["First Name"], row["Last Name"]
                phone, email = row["Phone"], row["Email"]
                company, job, website = row["Company"], row["Job Title"], row["Website"]
                dept, location = row.get("Department", ""), row.get("Location", "")
                vcard = create_vcard(first, last, phone, email, company, job, website, dept, location)

                folder = f"{first}_{last}"
                png = generate_qr_code(vcard, "PNG")
                svg = generate_qr_code(vcard, "SVG")

                zf.writestr(f"{folder}/{folder}.vcf", vcard)
                zf.writestr(f"{folder}/{folder}.png", png)
                zf.writestr(f"{folder}/{folder}.svg", svg)

        st.download_button("⬇️ Download Employee Directory (ZIP)", zip_buf.getvalue(), "employee_directory.zip", "application/zip")
