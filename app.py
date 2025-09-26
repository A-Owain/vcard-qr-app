import streamlit as st
import qrcode
import qrcode.image.svg
import pandas as pd
import os
import zipfile
import io
from PIL import Image
import barcode
from barcode.writer import ImageWriter

# ----------------------------
# Utility Functions
# ----------------------------

def create_qr_code(data, fmt="PNG"):
    if fmt == "SVG":
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(data, image_factory=factory)
    else:
        img = qrcode.make(data)
    return img

def save_qr_to_bytes(data, fmt="PNG"):
    buf = io.BytesIO()
    if fmt == "SVG":
        img = create_qr_code(data, fmt="SVG")
        img.save(buf)
        mime = "image/svg+xml"
    else:
        img = create_qr_code(data)
        img.save(buf, format="PNG")
        mime = "image/png"
    buf.seek(0)
    return buf, mime

def save_vcard_qr(first_name, last_name, phone, email, company, job, fmt="PNG"):
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{company}
TITLE:{job}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
END:VCARD"""
    return save_qr_to_bytes(vcard, fmt), vcard

def zip_files(files_dict):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for filename, filedata in files_dict.items():
            zf.writestr(filename, filedata.getvalue() if hasattr(filedata, "getvalue") else filedata)
    zip_buf.seek(0)
    return zip_buf

# ----------------------------
# Streamlit Tabs
# ----------------------------

st.set_page_config(page_title="QR & Barcode Suite", layout="wide")

tabs = st.tabs([
    "QR Code Generator",
    "Batch QR Generator",
    "vCard Generator",
    "Product Barcode",
    "Employee Directory"
])

# ----------------------------
# Tab 1 - QR Code Generator
# ----------------------------
with tabs[0]:
    st.header("QR Code Generator")
    data = st.text_input("Enter data/text for QR code")
    fmt = st.radio("Select format", ["PNG", "SVG"])
    if st.button("Generate QR"):
        if data:
            buf, mime = save_qr_to_bytes(data, fmt)
            st.image(buf, caption="Generated QR Code")
            st.download_button("Download", buf, file_name=f"qr_code.{fmt.lower()}", mime=mime)
        else:
            st.warning("Please enter some data.")

# ----------------------------
# Tab 2 - Batch QR Generator
# ----------------------------
with tabs[1]:
    st.header("Batch QR Generator")
    uploaded_file = st.file_uploader("Upload CSV/Excel with a 'Data' column", type=["csv", "xlsx"])
    fmt = st.radio("Select format", ["PNG", "SVG"], key="batch_fmt")
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if "Data" in df.columns:
            files = {}
            for i, row in df.iterrows():
                content = str(row["Data"])
                buf, _ = save_qr_to_bytes(content, fmt)
                files[f"{content}.{fmt.lower()}"] = buf
            zip_buf = zip_files(files)
            st.download_button("Download All as ZIP", zip_buf, "batch_qr_codes.zip", "application/zip")
        else:
            st.error("Uploaded file must contain a 'Data' column.")

# ----------------------------
# Tab 3 - vCard Generator
# ----------------------------
with tabs[2]:
    st.header("vCard QR Generator")
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        phone = st.text_input("Phone")
    with col2:
        email = st.text_input("Email")
        company = st.text_input("Company")
        job = st.text_input("Job Title")

    fmt = st.radio("Select format", ["PNG", "SVG"])
    if st.button("Generate vCard QR"):
        (buf, mime), vcard = save_vcard_qr(first_name, last_name, phone, email, company, job, fmt)
        st.image(buf, caption="vCard QR Code")
        st.download_button(f"Download vCard QR ({fmt})", buf, file_name=f"vcard_qr.{fmt.lower()}", mime=mime)
        st.download_button("Download .vcf file", vcard, file_name="contact.vcf", mime="text/vcard")

# ----------------------------
# Tab 4 - Product Barcode
# ----------------------------
with tabs[3]:
    st.header("Product Barcode Generator")
    data = st.text_input("Enter product code/value")
    barcode_type = st.selectbox("Barcode Type", ["code128", "ean13", "upc"])
    if st.button("Generate Barcode"):
        if data:
            try:
                BARCODE = barcode.get_barcode_class(barcode_type)
                buf = io.BytesIO()
                BARCODE(data, writer=ImageWriter()).write(buf)
                buf.seek(0)
                st.image(buf, caption=f"{barcode_type.upper()} Barcode")
                st.download_button("Download Barcode (PNG)", buf, file_name=f"barcode_{barcode_type}.png", mime="image/png")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter product data.")

# ----------------------------
# Tab 5 - Employee Directory
# ----------------------------
with tabs[4]:
    st.header("Employee Directory")
    st.write("Upload Excel with employee details to generate vCard QR codes.")

    # Downloadable template
    if st.button("Download Excel Template"):
        template = pd.DataFrame([{
            "First Name": "",
            "Last Name": "",
            "Phone": "",
            "Email": "",
            "Company": "",
            "Job Title": "",
            "Department": "",
            "Location": ""
        }])
        buf = io.BytesIO()
        template.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Download Template", buf, "employee_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    uploaded_file = st.file_uploader("Upload Employee Excel", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        required_cols = ["First Name", "Last Name", "Phone", "Email", "Company", "Job Title", "Department", "Location"]
        if all(col in df.columns for col in required_cols):
            files = {}
            for _, row in df.iterrows():
                (buf, _), vcard = save_vcard_qr(
                    row["First Name"], row["Last Name"],
                    row["Phone"], row["Email"],
                    row["Company"], row["Job Title"], fmt="PNG"
                )
                name = f"{row['First Name']}_{row['Last Name']}"
                files[f"{name}.png"] = buf
                files[f"{name}.vcf"] = io.BytesIO(vcard.encode("utf-8"))
            zip_buf = zip_files(files)
            st.download_button("Download All Employee Files (ZIP)", zip_buf, "employee_qrcards.zip", "application/zip")
        else:
            st.error(f"Excel must include: {', '.join(required_cols)}")
