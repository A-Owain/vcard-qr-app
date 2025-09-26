import streamlit as st
import pandas as pd
import qrcode
import io, os, zipfile, datetime
from PIL import Image
import barcode
from barcode.writer import ImageWriter
from vobject import vCard

# ========== Helper Functions ==========

def generate_vcard(first_name, last_name, phone, email, company, job_title, website, department, location):
    """Create a vCard string from employee data"""
    v = vCard()
    v.add('n').value = f"{last_name};{first_name}"
    v.add('fn').value = f"{first_name} {last_name}"
    if company: v.add('org').value = [company]
    if job_title: v.add('title').value = job_title
    if department: v.add('department').value = department
    if location: v.add('adr').value = location
    if phone: v.add('tel').value = phone
    if email: v.add('email').value = email
    if website: v.add('url').value = website
    return v.serialize()

def generate_qr_code(data, image_format='PNG'):
    """Generate QR code as bytes"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    output = io.BytesIO()
    img.save(output, format=image_format)
    return output.getvalue()

def save_employee_assets(row, base_dir):
    """Generate vCard, PNG, SVG for one employee"""
    first_name = row.get('First Name', '')
    last_name = row.get('Last Name', '')
    phone = row.get('Phone', '')
    email = row.get('Email', '')
    company = row.get('Company', '')
    job_title = row.get('Job Title', '')
    website = row.get('Website', '')
    department = row.get('Department', '')
    location = row.get('Location', '')

    # Folder
    folder_name = f"{first_name}_{last_name}".replace(" ", "_")
    folder_path = os.path.join(base_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # vCard
    vcard_data = generate_vcard(first_name, last_name, phone, email, company, job_title, website, department, location)
    vcf_path = os.path.join(folder_path, f"{folder_name}.vcf")
    with open(vcf_path, "w", encoding="utf-8") as f:
        f.write(vcard_data)

    # QR PNG
    qr_png_bytes = generate_qr_code(vcard_data, image_format='PNG')
    png_path = os.path.join(folder_path, f"{folder_name}.png")
    with open(png_path, "wb") as f:
        f.write(qr_png_bytes)

    # QR SVG
    qr_svg_bytes = generate_qr_code(vcard_data, image_format='PNG')  # we’ll still provide PNG for now (SVG is tricky)
    svg_path = os.path.join(folder_path, f"{folder_name}.svg")
    with open(svg_path, "wb") as f:
        f.write(qr_svg_bytes)

def create_zip_of_directory(dir_path):
    """Zip a directory and return as bytes"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, start=dir_path)
                zip_file.write(filepath, arcname)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def generate_excel_template():
    """Generate an Excel template for employees"""
    columns = ["First Name","Last Name","Phone","Email","Company","Job Title","Website","Department","Location"]
    df = pd.DataFrame(columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')
    output.seek(0)
    return output.getvalue()

# ========== Streamlit UI ==========

st.set_page_config(page_title="QR + vCard + Barcode Tool", layout="wide")

tab1, tab2, tab3, tab4 = st.tabs(["QR Generator", "vCard Generator", "Barcode Tool", "Employee Directory"])

# Placeholder for your existing tabs:
with tab1:
    st.subheader("QR Generator")
    st.write("Your existing QR generator code here…")

with tab2:
    st.subheader("vCard Generator")
    st.write("Your existing vCard generator code here…")

with tab3:
    st.subheader("Barcode Tool")
    st.write("Your existing Barcode code here…")

with tab4:
    st.subheader("Employee Directory Generator")

    # Download Template
    template_bytes = generate_excel_template()
    st.download_button("📥 Download Excel Template", data=template_bytes,
                       file_name="employee_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    uploaded_file = st.file_uploader("Upload filled Excel template", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        temp_dir = "temp_employees"
        os.makedirs(temp_dir, exist_ok=True)

        for _, row in df.iterrows():
            save_employee_assets(row, temp_dir)

        # Zip it
        zip_bytes = create_zip_of_directory(temp_dir)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        st.download_button("📦 Download All as ZIP",
                           data=zip_bytes,
                           file_name=f"Employee_Directory_{today}.zip",
                           mime="application/zip")
