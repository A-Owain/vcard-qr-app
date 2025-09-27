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
        "Position": "Marketing Lead",
        "Department": "Marketing",
        "Phone": "+966500000000",
        "Email": "abdurrahman@company.com",
        "Company": "Alraedah Finance",
        "Website": "https://alraedah.sa",
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
    date_part = datetime.now().strftime("%Y%m%d")
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
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Folder: {folder_name}\n"
        f"Total Employees Processed: {count}\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    return batch_path, summary

def export_batch_plain_qr(qr_df: pd.DataFrame, output_dir: str, custom_suffix: str | None = None):
    date_part = datetime.now().strftime("%Y%m%d")
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
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
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

# ------------------------------------------------------------
# Tab 3: Batch QR Codes
# ------------------------------------------------------------
with tabs[2]:
    st.markdown("### Batch QR Codes")
    st.write("Upload an Excel file with Label and Data columns.")

    uploaded_qr_excel = st.file_uploader("Upload Excel", type=["xlsx"], key="tab3_upload")
    custom_suffix_qr = st.text_input("Custom suffix", key="tab3_suffix")

    if st.button("Generate Batch QR Codes", key="tab3_generate"):
        if uploaded_qr_excel:
            qr_df = pd.read_excel(uploaded_qr_excel)
            batch_folder, summary = export_batch_plain_qr(qr_df, ".", custom_suffix=custom_suffix_qr)
            zip_buf = zip_directory(batch_folder)
            st.write("Batch QR codes generated.")
            st.text_area("Summary", summary, height=180, key="tab3_summary")
            st.download_button("Download ZIP", data=zip_buf, file_name=f"{os.path.basename(batch_folder)}.zip", mime="application/zip", key="tab3_dl_zip")
        else:
            st.write("Please upload a valid Excel file.")

# ------------------------------------------------------------
# Tab 4: Batch vCards
# ------------------------------------------------------------
with tabs[3]:
    st.markdown("### Batch vCards")
    st.write("Upload an Excel file with employee data. Required: FirstName, LastName, Phone, Email.")

    uploaded_emp_excel = st.file_uploader("Upload Employee Excel", type=["xlsx"], key="tab4_upload")
    custom_suffix_vc = st.text_input("Custom suffix", key="tab4_suffix")

    if st.button("Generate Batch vCards", key="tab4_generate"):
        if uploaded_emp_excel:
            emp_df = pd.read_excel(uploaded_emp_excel)
            batch_folder, summary = export_batch_vcards(emp_df, ".", custom_suffix=custom_suffix_vc)
            zip_buf = zip_directory(batch_folder)
            st.write("Batch vCards generated.")
            st.text_area("Summary", summary, height=180, key="tab4_summary")
            st.download_button("Download ZIP", data=zip_buf, file_name=f"{os.path.basename(batch_folder)}.zip", mime="application/zip", key="tab4_dl_zip")
        else:
            st.write("Please upload a valid Employee Excel file.")

# ------------------------------------------------------------
# Tab 5: Barcodes
# ------------------------------------------------------------
with tabs[4]:
    st.markdown("### Barcodes")
    st.write("Enter data to generate a barcode.")

    bc_type = st.selectbox("Barcode Type", ["Code128", "EAN13"], key="tab5_type")
    bc_data = st.text_input("Barcode Data", key="tab5_data")
    if st.button("Generate Barcode", key="tab5_generate"):
        if bc_data.strip():
            png = generate_barcode_png(bc_data.strip(), bc_type)
            st.write("Barcode generated.")
            st.image(io.BytesIO(png), caption="Barcode")
            st.download_button("Download Barcode", data=png, file_name=f"{bc_type}_barcode.png", mime="image/png", key="tab5_dl")
        else:
            st.write("Please enter data.")

# ------------------------------------------------------------
# Tab 6: Employee Directory
# ------------------------------------------------------------
with tabs[5]:
    st.markdown("### Employee Directory")
    st.write("Download the template, fill employee data, then upload it back for processing.")

    # Download template
    st.download_button("Download Employee Directory Template",
                       data=generate_employee_template_xlsx(),
                       file_name="Employee_Directory_Template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="tab6_dl")

    # Upload filled file
    uploaded_dir_excel = st.file_uploader("Upload filled Employee Directory Excel", type=["xlsx"], key="tab6_upload")

    # Custom naming input
    custom_name = st.text_input("Custom name for this directory (optional)", key="tab6_name")

    if uploaded_dir_excel:
        df = pd.read_excel(uploaded_dir_excel)
        st.write("Preview of uploaded data:")
        st.dataframe(df.head())

        # Example: Save processed directory as CSV with custom name
        filename = f"Employee_Directory_{custom_name or 'Export'}.csv"
        csv_bytes = df.to_csv(index=False).encode("utf-8")

        st.download_button("Download Processed Directory",
                           data=csv_bytes,
                           file_name=filename,
                           mime="text/csv",
                           key="tab6_processed")

# ------------------------------------------------------------
# Tab 7: Templates & Help
# ------------------------------------------------------------
with tabs[6]:
    st.markdown("### Templates & Help")

    col1, col2 = st.columns(2)

    # English section (left, bordered box)
    with col1:
        st.markdown(
            """
            <div style="border:1px solid #ccc; border-radius:8px; padding:15px; margin-bottom:10px;">
                <h4>Employee Directory Template:</h4>
                <ul>
                  <li>Required: FirstName, LastName, Phone, Email</li>
                  <li>Optional: Position, Department, Company, Website, Location, MapsLink, Notes</li>
                  <li>Includes one sample row for guidance.</li>
                </ul>
                <p><b>Batch QR Template:</b></p>
                <ul>
                  <li>Required: Label, Data</li>
                  <li>Includes one sample row for guidance.</li>
                </ul>
                <p><b>Notes:</b></p>
                <ul>
                  <li>All batch exports include a SUMMARY.txt file.</li>
                  <li>Website and MapsLink are added as separate URL lines in vCards.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Arabic section (right, bordered box with RTL)
    with col2:
        st.markdown(
            """
            <div style="border:1px solid #ccc; border-radius:8px; padding:15px; margin-bottom:10px;" dir="rtl">
                <h4>قالب دليل الموظفين:</h4>
                <ul>
                  <li>الأعمدة المطلوبة: FirstName, LastName, Phone, Email</li>
                  <li>الأعمدة الاختيارية: Position, Department, Company, Website, Location, MapsLink, Notes</li>
                  <li>يحتوي على صف تجريبي للتوضيح.</li>
                </ul>
                <p><b>قالب الأكواد (Batch QR):</b></p>
                <ul>
                  <li>الأعمدة المطلوبة: Label, Data</li>
                  <li>يحتوي على صف تجريبي للتوضيح.</li>
                </ul>
                <p><b>ملاحظات:</b></p>
                <ul>
                  <li>جميع المخرجات تحتوي ملف SUMMARY.txt</li>
                  <li>موقع الشركة (Website) ورابط الخرائط (MapsLink) يتم إضافتهم كسطرين URL في بطاقة vCard.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Downloads
    st.download_button("Download Employee Directory Template", data=generate_employee_template_xlsx(),
                       file_name="Employee_Directory_Template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="tab7_dl1")
    st.download_button("Download Batch QR Template", data=generate_batch_qr_template_xlsx(),
                       file_name="Batch_QR_Template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="tab7_dl2")

    # Contact info
    st.markdown(
    """
    <div style="border:1px solid #ccc; border-radius:8px; padding:15px; margin-top:15px;">
        <p><b>For more help, please contact:</b></p>
        <p>Abdurrahman Alowain – Product Designer & Developer</p>
        <p>
          <a href="mailto:abdurrahmanowain@gmail.com" target="_blank">Email</a> | 
          <a href="https://www.linkedin.com/in/abdurrahnmanowain/" target="_blank">LinkedIn</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# Footer (global for all tabs)
# ============================================================
st.markdown(
    """
    <hr style="margin-top:50px; margin-bottom:10px;">
    <div style="text-align:center; color:gray; font-size:13px;">
    © 2025 Developed By Abdurrahman Alowain. All rights reserved. | 
    Follow me on <a href="https://www.x.com/a_owain" target="_blank">X (Twitter)</a>
    </div>
    """,
    unsafe_allow_html=True
)
