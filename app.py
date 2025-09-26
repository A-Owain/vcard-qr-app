import streamlit as st
import qrcode
import pandas as pd
import os
import zipfile
from io import BytesIO
from datetime import datetime
from PIL import Image
import barcode
from barcode.writer import ImageWriter

# App Title
st.set_page_config(page_title="QR & Barcode Generator", page_icon="🔗", layout="wide")
st.title("🔗 QR & Barcode Generator")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📇 QR vCard", 
    "📦 Batch QR Generator", 
    "🛠 Other Tools", 
    "🏷 Product Barcode"
])

# -------------------
# Tab 1: QR vCard
# -------------------
with tab1:
    st.header("📇 Create a vCard QR Code")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    org = st.text_input("Organization")
    title = st.text_input("Job Title")
    website = st.text_input("Website")
    
    if st.button("Generate vCard QR"):
        vcard_data = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{org}
TITLE:{title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
URL:{website}
END:VCARD"""
        
        qr = qrcode.make(vcard_data)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        st.image(qr, caption="Your vCard QR", use_column_width=True)
        st.download_button(
            "Download vCard QR",
            buffer,
            file_name=f"{first_name}_{last_name}_vcard.png",
            mime="image/png"
        )

# -------------------
# Tab 2: Batch QR Generator
# -------------------
with tab2:
    st.header("📦 Batch QR Generator from Excel")

    uploaded_file = st.file_uploader("Upload Excel with contacts", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Preview of uploaded file:", df.head())
        
        if st.button("Generate Batch QR Codes"):
            date_str = datetime.now().strftime("%Y%m%d")
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for _, row in df.iterrows():
                    first_name = row.get("First Name", "")
                    last_name = row.get("Last Name", "")
                    phone = row.get("Phone", "")
                    email = row.get("Email", "")
                    org = row.get("Organization", "")
                    title = row.get("Title", "")
                    website = row.get("Website", "")

                    vcard_data = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{first_name} {last_name}
ORG:{org}
TITLE:{title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
URL:{website}
END:VCARD"""

                    qr = qrcode.make(vcard_data)
                    qr_buffer = BytesIO()
                    qr.save(qr_buffer, format="PNG")
                    qr_buffer.seek(0)

                    filename = f"{first_name}_{last_name}.png"
                    zipf.writestr(filename, qr_buffer.getvalue())

            zip_buffer.seek(0)

            st.success("Batch QR codes generated!")
            st.download_button(
                "Download All as ZIP",
                zip_buffer,
                file_name=f"Batch_QR_vCards_{date_str}.zip",
                mime="application/zip"
            )

# -------------------
# Tab 3: Other Tools
# -------------------
with tab3:
    st.header("🛠 Other Tools")
    st.info("More tools coming soon!")

# -------------------
# Tab 4: Product Barcode
# -------------------
with tab4:
    st.header("🏷 Product Barcode Generator")

    product_text = st.text_input("Enter product code or text:")
    barcode_type = st.selectbox(
        "Choose barcode format:",
        ["code128", "ean13", "upc", "isbn13"]
    )

    if st.button("Generate Barcode"):
        if product_text.strip():
            try:
                BARCODE_CLASS = barcode.get_barcode_class(barcode_type)
                buffer = BytesIO()
                BARCODE_CLASS(product_text, writer=ImageWriter()).write(buffer)

                buffer.seek(0)
                img = Image.open(buffer)

                st.image(img, caption="Generated Barcode", use_column_width=True)

                st.download_button(
                    "Download Barcode PNG",
                    buffer,
                    file_name=f"barcode_{product_text}.png",
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a product code or text.")
