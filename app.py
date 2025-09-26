import streamlit as st
import qrcode
import pandas as pd
import io
import zipfile
import os
from PIL import Image
import barcode
from barcode.writer import ImageWriter

# --------------------------
# Utility Functions
# --------------------------

def generate_qr(data, box_size=10, border=4):
    qr = qrcode.QRCode(
        version=1,
        box_size=box_size,
        border=border
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def download_button(file_bytes, file_name, file_label):
    st.download_button(
        label=file_label,
        data=file_bytes,
        file_name=file_name
    )

# --------------------------
# Streamlit Tabs
# --------------------------

st.set_page_config(page_title="Business Tools Hub", layout="wide")

tabs = st.tabs([
    "📇 vCard QR",
    "📦 Product Barcode",
    "👥 Employee Directory",
    "📊 Business Card QR",
    "🔗 URL / Link QR",
    "📧 Email QR",
    "📱 SMS / WhatsApp QR",
    "💵 Payment QR"
])

# --------------------------
# 1. vCard QR Generator
# --------------------------
with tabs[0]:
    st.header("📇 vCard QR Generator")
    first = st.text_input("First Name")
    last = st.text_input("Last Name")
    phone = st.text_input("Phone")
    email = st.text_input("Email")
    org = st.text_input("Organization")
    title = st.text_input("Job Title")

    if st.button("Generate vCard QR"):
        vcard_data = f"""BEGIN:VCARD
VERSION:3.0
N:{last};{first};;;
FN:{first} {last}
ORG:{org}
TITLE:{title}
TEL:{phone}
EMAIL:{email}
END:VCARD"""
        img = generate_qr(vcard_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(img, caption="vCard QR Code", use_container_width=False)

        # Downloads
        download_button(buf.getvalue(), "vcard.png", "⬇️ Download PNG")
        download_button(vcard_data.encode(), "vcard.vcf", "⬇️ Download VCF")

# --------------------------
# 2. Product Barcode
# --------------------------
with tabs[1]:
    st.header("📦 Product Barcode Generator")
    product_code = st.text_input("Enter Product Code")
    barcode_type = st.selectbox("Select Barcode Type", ["code128", "ean13", "upc"])

    if st.button("Generate Barcode"):
        try:
            BARCODE = barcode.get_barcode_class(barcode_type)
            bar_img = BARCODE(product_code, writer=ImageWriter())
            buf = io.BytesIO()
            bar_img.write(buf)
            buf.seek(0)
            st.image(buf, caption="Generated Barcode")

            download_button(buf.getvalue(), f"barcode_{barcode_type}.png", "⬇️ Download PNG")
        except Exception as e:
            st.error(f"Error: {e}")

# --------------------------
# 3. Employee Directory
# --------------------------
with tabs[2]:
    st.header("👥 Employee Directory Batch Generator")

    st.write("📥 Download Excel template, fill it, then upload it back.")
    template = pd.DataFrame({
        "First Name": [],
        "Last Name": [],
        "Phone": [],
        "Email": [],
        "Department": [],
        "Location": []
    })
    template_buf = io.BytesIO()
    template.to_excel(template_buf, index=False)
    download_button(template_buf.getvalue(), "employee_template.xlsx", "⬇️ Download Excel Template")

    uploaded = st.file_uploader("Upload Completed Employee Excel", type=["xlsx"])
    if uploaded:
        df = pd.read_excel(uploaded)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zipf:
            for _, row in df.iterrows():
                vcard_data = f"""BEGIN:VCARD
VERSION:3.0
N:{row['Last Name']};{row['First Name']};;;
FN:{row['First Name']} {row['Last Name']}
TEL:{row['Phone']}
EMAIL:{row['Email']}
ORG:{row['Department']}
TITLE:{row['Location']}
END:VCARD"""
                img = generate_qr(vcard_data)
                fname = f"{row['First Name']}_{row['Last Name']}.png"
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zipf.writestr(fname, buf.getvalue())
                zipf.writestr(f"{row['First Name']}_{row['Last Name']}.vcf", vcard_data)
        zip_buf.seek(0)
        download_button(zip_buf.getvalue(), "employees_qr.zip", "⬇️ Download ZIP with all files")

# --------------------------
# 4. Business Card QR
# --------------------------
with tabs[3]:
    st.header("📊 Business Card QR")
    name = st.text_input("Full Name")
    title = st.text_input("Title")
    company = st.text_input("Company")
    website = st.text_input("Website")

    if st.button("Generate Business Card QR"):
        data = f"{name}\n{title}\n{company}\n{website}"
        img = generate_qr(data)
        st.image(img, caption="Business Card QR")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        download_button(buf.getvalue(), "business_card.png", "⬇️ Download PNG")

# --------------------------
# 5. URL / Link QR
# --------------------------
with tabs[4]:
    st.header("🔗 URL / Link QR")
    url = st.text_input("Enter URL")
    if st.button("Generate URL QR"):
        img = generate_qr(url)
        st.image(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        download_button(buf.getvalue(), "url_qr.png", "⬇️ Download PNG")

# --------------------------
# 6. Email QR
# --------------------------
with tabs[5]:
    st.header("📧 Email QR")
    recipient = st.text_input("Recipient Email")
    subject = st.text_input("Subject")
    body = st.text_area("Body")

    if st.button("Generate Email QR"):
        mailto = f"mailto:{recipient}?subject={subject}&body={body}"
        img = generate_qr(mailto)
        st.image(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        download_button(buf.getvalue(), "email_qr.png", "⬇️ Download PNG")

# --------------------------
# 7. SMS / WhatsApp QR
# --------------------------
with tabs[6]:
    st.header("📱 SMS / WhatsApp QR")
    phone = st.text_input("Phone Number (with country code)")
    msg = st.text_area("Message")

    option = st.radio("Choose", ["SMS", "WhatsApp"])
    if st.button("Generate Messaging QR"):
        if option == "SMS":
            data = f"sms:{phone}?body={msg}"
        else:
            data = f"https://wa.me/{phone}?text={msg}"
        img = generate_qr(data)
        st.image(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        download_button(buf.getvalue(), "message_qr.png", "⬇️ Download PNG")

# --------------------------
# 8. Payment QR
# --------------------------
with tabs[7]:
    st.header("💵 Payment QR")
    method = st.selectbox("Payment Method", ["Bank Transfer", "PayPal", "Custom Link"])
    data = ""
    if method == "Bank Transfer":
        iban = st.text_input("IBAN")
        name = st.text_input("Account Holder")
        data = f"Bank Transfer\nIBAN: {iban}\nName: {name}"
    elif method == "PayPal":
        paypal_email = st.text_input("PayPal Email")
        data = f"https://paypal.me/{paypal_email}"
    else:
        link = st.text_input("Custom Payment Link")
        data = link

    if st.button("Generate Payment QR"):
        img = generate_qr(data)
        st.image(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        download_button(buf.getvalue(), "payment_qr.png", "⬇️ Download PNG")
