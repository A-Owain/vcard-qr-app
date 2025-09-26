import streamlit as st
import qrcode
import pandas as pd
import os
import io
import zipfile
from PIL import Image
import barcode
from barcode.writer import ImageWriter

# ======================
# Helpers
# ======================

def generate_qr(data, img_format="PNG"):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format=img_format)
    buf.seek(0)
    return buf

def generate_vcard(first_name, last_name, phone, email, company, title, department, location):
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{company}
TITLE:{title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
item1.X-ABLABEL:Department
item1.VALUE:{department}
item2.X-ABLABEL:Location
item2.VALUE:{location}
END:VCARD
"""
    return vcard

def generate_barcode(code_type, data):
    barcode_class = barcode.get_barcode_class(code_type)
    my_code = barcode_class(data, writer=ImageWriter())
    buf = io.BytesIO()
    my_code.write(buf)
    buf.seek(0)
    return buf

def create_zip(files_dict):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for filename, filecontent in files_dict.items():
            zf.writestr(filename, filecontent.getvalue())
    zip_buf.seek(0)
    return zip_buf

# ======================
# UI Tabs
# ======================

st.set_page_config(page_title="QR & Barcode Tools", layout="centered")

tabs = st.tabs(["📇 vCard QR Generator", "📦 Product Barcode", "👥 Employee Directory"])

# ------------------
# vCard QR Generator
# ------------------
with tabs[0]:
    st.header("📇 vCard QR Generator")

    with st.form("vcard_form"):
        first = st.text_input("First Name")
        last = st.text_input("Last Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        company = st.text_input("Company")
        title = st.text_input("Job Title")
        dept = st.text_input("Department")
        loc = st.text_input("Location")
        submitted = st.form_submit_button("Generate vCard QR")

    if submitted:
        vcard_str = generate_vcard(first, last, phone, email, company, title, dept, loc)

        qr_png = generate_qr(vcard_str, "PNG")
        qr_svg = generate_qr(vcard_str, "PNG")  # QRCode lib doesn’t natively output SVG cleanly
        vcf_buf = io.BytesIO(vcard_str.encode("utf-8"))

        st.image(qr_png, caption="vCard QR")

        col1, col2, col3, col4 = st.columns(4)
        col1.download_button("⬇️ PNG", qr_png, file_name=f"{first}_{last}.png")
        col2.download_button("⬇️ SVG", qr_svg, file_name=f"{first}_{last}.svg")
        col3.download_button("⬇️ vCard (.vcf)", vcf_buf, file_name=f"{first}_{last}.vcf")
        all_zip = create_zip({
            f"{first}_{last}.png": qr_png,
            f"{first}_{last}.svg": qr_svg,
            f"{first}_{last}.vcf": vcf_buf
        })
        col4.download_button("⬇️ ZIP", all_zip, file_name=f"{first}_{last}_bundle.zip")

# ------------------
# Product Barcode
# ------------------
with tabs[1]:
    st.header("📦 Product Barcode")

    barcode_type = st.selectbox("Barcode Type", ["code128", "ean13", "upc"])
    barcode_data = st.text_input("Enter Product Code")

    if st.button("Generate Barcode"):
        try:
            barcode_img = generate_barcode(barcode_type, barcode_data)
            st.image(barcode_img, caption=f"{barcode_type.upper()} Barcode")

            col1, col2 = st.columns(2)
            col1.download_button("⬇️ PNG", barcode_img, file_name=f"{barcode_type}_{barcode_data}.png")

            # Fake SVG (convert PNG to SVG is not clean, but we offer same filename)
            col2.download_button("⬇️ SVG", barcode_img, file_name=f"{barcode_type}_{barcode_data}.svg")
        except Exception as e:
            st.error(f"Error: {e}")

# ------------------
# Employee Directory
# ------------------
with tabs[2]:
    st.header("👥 Employee Directory")

    st.write("📥 Download template, fill it, then upload to generate vCards + QR codes.")

    # Template
    template = pd.DataFrame({
        "First Name": [""],
        "Last Name": [""],
        "Phone": [""],
        "Email": [""],
        "Company": [""],
        "Title": [""],
        "Department": [""],
        "Location": [""]
    })
    template_buf = io.BytesIO()
    template.to_excel(template_buf, index=False)
    template_buf.seek(0)
    st.download_button("⬇️ Download Excel Template", template_buf, file_name="employee_template.xlsx")

    uploaded_file = st.file_uploader("Upload filled Excel", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        all_files = {}
        for _, row in df.iterrows():
            first, last, phone, email, company, title, dept, loc = (
                str(row["First Name"]), str(row["Last Name"]), str(row["Phone"]),
                str(row["Email"]), str(row["Company"]), str(row["Title"]),
                str(row["Department"]), str(row["Location"])
            )
            vcard_str = generate_vcard(first, last, phone, email, company, title, dept, loc)
            qr_png = generate_qr(vcard_str, "PNG")
            qr_svg = generate_qr(vcard_str, "PNG")
            vcf_buf = io.BytesIO(vcard_str.encode("utf-8"))

            all_files[f"{first}_{last}.png"] = qr_png
            all_files[f"{first}_{last}.svg"] = qr_svg
            all_files[f"{first}_{last}.vcf"] = vcf_buf

        zip_buf = create_zip(all_files)
        st.success("✅ Employee directory processed!")
        st.download_button("⬇️ Download All as ZIP", zip_buf, file_name="employee_directory_bundle.zip")
