# ============================================================
# QR, Barcodes & Employee Directory App (Minimal + English UI, Bilingual Help in Last Tab)
# ============================================================

import streamlit as st
import pandas as pd
import os
import io
import zipfile
import qrcode
import qrcode.image.svg
from barcode import Code128, EAN13
from barcode.writer import ImageWriter
from datetime import datetime
from zoneinfo import ZoneInfo   # ✅ added for timezone

# ------------------------------------------------------------
# Timezone helpers
# ------------------------------------------------------------
LOCAL_TZ = ZoneInfo("Asia/Riyadh")

def today_local_date() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y%m%d")

def now_local_str() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")

# ------------------------------------------------------------
# Helpers: QR encoders (PNG / SVG)
# ------------------------------------------------------------
def qr_png_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def qr_svg_bytes(data: str) -> bytes:
    factory = qrcode.image.svg.SvgImage
    svg_img = qrcode.make(data, image_factory=factory)
    buf = io.BytesIO()
    svg_img.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ------------------------------------------------------------
# vCard generator
# ------------------------------------------------------------
def create_vcard(employee: dict) -> str:
    v = []
    v.append("BEGIN:VCARD")
    v.append("VERSION:3.0")
    v.append(f"N:{employee.get('LastName','')};{employee.get('FirstName','')};;;")
    v.append(f"FN:{employee.get('FirstName','')} {employee.get('LastName','')}")
    v.append(f"ORG:{employee.get('Company','')}")
    v.append(f"TITLE:{employee.get('Position','')}")
    if employee.get("Phone"):
        v.append(f"TEL;TYPE=CELL,VOICE:{employee['Phone']}")
    if employee.get("Email"):
        v.append(f"EMAIL;TYPE=PREF,INTERNET:{employee['Email']}")
    if employee.get("Department"):
        v.append(f"NOTE:Department - {employee['Department']}")
    if employee.get("Location"):
        v.append(f"ADR;TYPE=WORK:;;{employee['Location']}")
    if employee.get("Website"):
        v.append(f"URL:{employee['Website']}")
    if employee.get("MapsLink"):
        v.append(f"URL:{employee['MapsLink']}")
    if employee.get("Notes"):
        v.append(f"NOTE:{employee['Notes']}")
    v.append("END:VCARD")
    return "\n".join(v)

# ------------------------------------------------------------
# Excel template generators
# ------------------------------------------------------------
def generate_employee_template_xlsx() -> bytes:
    columns = [
        "FirstName", "LastName", "Position", "Department",
        "Phone", "Email", "Company", "Website",
        "Location", "MapsLink", "Notes"
    ]
    sample_row = [{
        "FirstName": "Abdurrahman",
        "LastName": "Alowain",
        "Position": "Product Designer",
        "Department": "Design",
        "Phone": "+966500000000",
        "Email": "abdurrahman@topsecret.com",
        "Company": "Top Secret Co.",
        "Website": "https://topsecret.com",
        "Location": "Riyadh HQ, Saudi Arabia",
        "MapsLink": "https://maps.app.goo.gl/example",
        "Notes": "Sample entry for testing"
    }]
    df = pd.DataFrame(sample_row, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Employees")
    return output.getvalue()

def generate_batch_qr_template_xlsx() -> bytes:
    columns = ["Label", "Data"]
    sample = [{"Label": "Website", "Data": "https://alraedah.sa"}]
    df = pd.DataFrame(sample, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="QR_Data")
    return output.getvalue()

# ------------------------------------------------------------
# ZIP utility
# ------------------------------------------------------------
def zip_directory(folder_path: str) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, folder_path)
                zipf.write(fpath, arcname)
    zip_buffer.seek(0)
    return zip_buffer

# ------------------------------------------------------------
# Batch exporters
# ------------------------------------------------------------
def export_batch_vcards(employees_df: pd.DataFrame, output_dir: str, custom_suffix: str | None = None):
    date_part = today_local_date()
    folder_name = f"Batch_QR_vCards_{date_part}" + (f"_{custom_suffix}" if custom_suffix else "")
    batch_path = os.path.join(output_dir, folder_name)
    os.makedirs(batch_path, exist_ok=True)

    count = 0
    for _, row in employees_df.iterrows():
        first = str(row.get("FirstName", "")).strip()
        last = str(row.get("LastName", "")).strip()
        subfolder = f"{first}_{last}".replace(" ", "_") or "Employee"
        emp_dir = os.path.join(batch_path, subfolder)
        os.makedirs(emp_dir, exist_ok=True)

        vcard = create_vcard(row.to_dict())
        with open(os.path.join(emp_dir, f"{subfolder}.vcf"), "w", encoding="utf-8") as f:
            f.write(vcard)
        with open(os.path.join(emp_dir, f"{subfolder}.png"), "wb") as f:
            f.write(qr_png_bytes(vcard))
        with open(os.path.join(emp_dir, f"{subfolder}.svg"), "wb") as f:
            f.write(qr_svg_bytes(vcard))
        count += 1

    summary = (
        "Batch vCards Export\n"
        f"Date (Asia/Riyadh): {now_local_str()}\n"
        f"Folder: {folder_name}\n"
        f"Total Employees Processed: {count}\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    return batch_path, summary

def export_batch_plain_qr(qr_df: pd.DataFrame, output_dir: str, custom_suffix: str | None = None):
    date_part = today_local_date()
    folder_name = f"Batch_QR_Plain_{date_part}" + (f"_{custom_suffix}" if custom_suffix else "")
    batch_path = os.path.join(output_dir, folder_name)
    os.makedirs(batch_path, exist_ok=True)

    count = 0
    for _, row in qr_df.iterrows():
        label = str(row.get("Label", "")).strip() or f"Item_{count+1}"
        data = str(row.get("Data", "")).strip()
        label_sanitized = label.replace(" ", "_")
        item_dir = os.path.join(batch_path, label_sanitized)
        os.makedirs(item_dir, exist_ok=True)

        with open(os.path.join(item_dir, f"{label_sanitized}.png"), "wb") as f:
            f.write(qr_png_bytes(data))
        with open(os.path.join(item_dir, f"{label_sanitized}.svg"), "wb") as f:
            f.write(qr_svg_bytes(data))
        count += 1

    summary = (
        "Batch Plain QR Export\n"
        f"Date (Asia/Riyadh): {now_local_str()}\n"
        f"Folder: {folder_name}\n"
        f"Total Items Processed: {count}\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    return batch_path, summary

# ------------------------------------------------------------
# Barcode generator
# ------------------------------------------------------------
def generate_barcode_png(data: str, barcode_type: str = "Code128") -> bytes:
    buf = io.BytesIO()
    if barcode_type == "Code128":
        Code128(data, writer=ImageWriter()).write(buf)
    elif barcode_type == "EAN13":
        data = "".join(ch for ch in str(data) if ch.isdigit())
        data = data.zfill(12)[:12]
        EAN13(data, writer=ImageWriter()).write(buf)
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# Streamlit UI
# ============================================================
st.set_page_config(page_title="QR, Barcodes & Employee Directory", layout="wide")
st.title("QR, Barcodes & Employee Directory")

tabs = st.tabs([
    "Single QR Code",
    "Single vCard",
    "Batch QR Codes",
    "Batch vCards",
    "Barcodes",
    "Employee Directory",
    "Templates & Help"
])

# ------------------------------------------------------------
# Tab 1: Single QR Code
# ------------------------------------------------------------
with tabs[0]:
    st.markdown("### Single QR Code")
    st.write("Enter text or URL to generate a QR code in PNG or SVG.")

    qr_text = st.text_input("Text or URL", key="tab1_qr_text")
    if st.button("Generate QR", key="tab1_generate"):
        if qr_text.strip():
            png = qr_png_bytes(qr_text.strip())
            svg = qr_svg_bytes(qr_text.strip())
            st.write("QR generated successfully.")
            st.image(io.BytesIO(png), caption="QR Code")
            st.download_button("Download PNG", data=png, file_name="qr.png", mime="image/png", key="tab1_dl_png")
            st.download_button("Download SVG", data=svg, file_name="qr.svg", mime="image/svg+xml", key="tab1_dl_svg")
        else:
            st.write("Please enter text or a URL.")

# ------------------------------------------------------------
# Tab 2: Single vCard
# ------------------------------------------------------------
with tabs[1]:
    st.markdown("### Single vCard")
    st.write("Fill the fields to generate a vCard with QR.")

    first = st.text_input("First Name", key="tab2_first")
    last = st.text_input("Last Name", key="tab2_last")
    company = st.text_input("Company", key="tab2_company")
    position = st.text_input("Position", key="tab2_position")
    dept = st.text_input("Department", key="tab2_dept")
    phone = st.text_input("Phone", key="tab2_phone")
    email = st.text_input("Email", key="tab2_email")
    website = st.text_input("Website", key="tab2_website")
    location = st.text_input("Location", key="tab2_location")
    mapslink = st.text_input("Google Maps Link", key="tab2_mapslink")
    notes = st.text_area("Notes", key="tab2_notes")

    if st.button("Generate vCard", key="tab2_generate"):
        emp = {"FirstName": first, "LastName": last, "Company": company, "Position": position, "Department": dept,
               "Phone": phone, "Email": email, "Website": website, "Location": location, "MapsLink": mapslink,
               "Notes": notes}
        vcard = create_vcard(emp)
        st.write("vCard generated successfully.")
        st.download_button("Download vCard (.vcf)", data=vcard, file_name=f"{first}_{last}.vcf", mime="text/vcard", key="tab2_dl_vcf")
        png = qr_png_bytes(vcard)
        svg = qr_svg_bytes(vcard)
        st.image(io.BytesIO(png), caption="vCard QR Code")
        st.download_button("Download QR (PNG)", data=png, file_name=f"{first}_{last}.png", mime="image/png", key="tab2_dl_png")
        st.download_button("Download QR (SVG)", data=svg, file_name=f"{first}_{last}.svg", mime="image/svg+xml", key="tab2_dl_svg")

        # ✅ New: ZIP all files together
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{first}_{last}.vcf", vcard)
            zf.writestr(f"{first}_{last}.png", png)
            zf.writestr(f"{first}_{last}.svg", svg)
        zip_buf.seek(0)
        st.download_button(
            "Download All (ZIP)",
            data=zip_buf,
            file_name=f"{first}_{last}_{today_local_date()}.zip",
            mime="application/zip",
            key="tab2_dl_zip"
        )