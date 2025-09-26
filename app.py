# ============================================================
# 📇 QR, Barcodes & Employee Directory App (Full Multi-Tab, Unique Keys)
# - Single QR Code (plain text/URL) → PNG + SVG
# - Single vCard (dual URL: Website + MapsLink) → .vcf + PNG + SVG
# - Batch QR Codes (non-vCard) from Excel (Label, Data) → folders + SUMMARY.txt + ZIP
# - Batch vCards from Excel (employee directory) → folders + SUMMARY.txt + ZIP
# - Barcodes (Code128, EAN13) → PNG
# - Employee Directory (guide + sample row + template download)
# - Templates & Help (overview + downloads)
# Dependencies: streamlit, pandas, qrcode, python-barcode, openpyxl
# No svgwrite required (SVG via qrcode.image.svg).
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
    """Return PNG bytes for the given data as a QR code."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def qr_svg_bytes(data: str) -> bytes:
    """Return SVG bytes for the given data as a QR code (no svgwrite needed)."""
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
    """
    Create a vCard string from an employee dictionary.
    Includes dual URL lines (Website + MapsLink when provided).
    """
    v = []
    v.append("BEGIN:VCARD")
    v.append("VERSION:3.0")
    v.append(f"N:{employee.get('LastName','')};{employee.get('FirstName','')};;;")
    v.append(f"FN:{employee.get('FirstName','')} {employee.get('LastName','')}")
    v.append(f"ORG:{employee.get('Company','')}")
    v.append(f"TITLE:{employee.get('Position','')}")
    # Phone
    if employee.get("Phone"):
        v.append(f"TEL;TYPE=CELL,VOICE:{employee['Phone']}")
    # Email
    if employee.get("Email"):
        v.append(f"EMAIL;TYPE=PREF,INTERNET:{employee['Email']}")
    # Department as NOTE (optional)
    if employee.get("Department"):
        v.append(f"NOTE:Department - {employee['Department']}")
    # Address (simple mapping to street component)
    if employee.get("Location"):
        v.append(f"ADR;TYPE=WORK:;;{employee['Location']}")
    # Website
    if employee.get("Website"):
        v.append(f"URL:{employee['Website']}")
    # Maps link as second URL
    if employee.get("MapsLink"):
        v.append(f"URL:{employee['MapsLink']}")
    # Notes
    if employee.get("Notes"):
        v.append(f"NOTE:{employee['Notes']}")
    v.append("END:VCARD")
    return "\n".join(v)

# ------------------------------------------------------------
# Excel template generators
# ------------------------------------------------------------
def generate_employee_template_xlsx() -> bytes:
    """
    Employee Directory template (.xlsx) with a sample row for guidance.
    """
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
    """
    Batch QR (non-vCard) template (.xlsx) with a sample row (Label, Data).
    """
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
    """
    Compress folder_path into an in-memory ZIP file and return the buffer.
    """
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
    """
    Export batch of vCards + QR (.png / .svg) from employees DataFrame.
    Creates:
      /Batch_QR_vCards_YYYYMMDD[_suffix]/
        /First_Last/
          First_Last.vcf
          First_Last.png
          First_Last.svg
      SUMMARY.txt
    Returns: (batch_folder_path, summary_text)
    """
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
        "Batch QR & vCards Export\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Folder: {folder_name}\n"
        f"Total Employees Processed: {count}\n\n"
        "Each employee folder contains:\n"
        "- .vcf (vCard)\n"
        "- .png (QR Code)\n"
        "- .svg (QR Code)\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)

    return batch_path, summary

def export_batch_plain_qr(qr_df: pd.DataFrame, output_dir: str, custom_suffix: str | None = None):
    """
    Export batch of plain QR codes from (Label, Data) DataFrame.
    Creates:
      /Batch_QR_Plain_YYYYMMDD[_suffix]/
        /Label/
          Label.png
          Label.svg
      SUMMARY.txt
    Returns: (batch_folder_path, summary_text)
    """
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
        f"Total Items Processed: {count}\n\n"
        "Each item folder contains:\n"
        "- .png (QR Code)\n"
        "- .svg (QR Code)\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)

    return batch_path, summary

# ------------------------------------------------------------
# Barcode generator
# ------------------------------------------------------------
def generate_barcode_png(data: str, barcode_type: str = "Code128") -> bytes:
    """
    Generate a barcode PNG as bytes. Supports Code128 and EAN13.
    """
    buf = io.BytesIO()
    if barcode_type == "Code128":
        Code128(data, writer=ImageWriter()).write(buf)
    elif barcode_type == "EAN13":
        # EAN13 must be 12 digits; 13th checksum is auto-generated.
        data = "".join(ch for ch in str(data) if ch.isdigit())
        data = data.zfill(12)[:12]
        EAN13(data, writer=ImageWriter()).write(buf)
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# Streamlit UI
# ============================================================
st.set_page_config(page_title="QR, Barcodes & Employee Directory", layout="wide")
st.title("📇 QR, Barcodes & Employee Directory — Full Suite")

tabs = st.tabs([
    "Single QR Code",
    "Single vCard",
    "Batch QR Codes",
    "Batch vCards",
    "Barcodes",
    "Employee Directory",
    "Templates & Help"
])

# ============================================================
# Tab 1: Single QR Code (plain)
# ============================================================
with tabs[0]:
    st.subheader("Single QR Code (Plain Text / URL)")
    st.markdown("Enter any text or URL and get a QR in PNG & SVG.")

    qr_text = st.text_input("Enter text or URL to encode", key="tab1_qr_text")
    if st.button("Generate QR", key="tab1_generate"):
        if qr_text.strip():
            png = qr_png_bytes(qr_text.strip())
            svg = qr_svg_bytes(qr_text.strip())
            st.success("✅ QR generated")
            st.image(io.BytesIO(png), caption="QR Code (PNG)", use_column_width=False)
            c1, c2 = st.columns(2)
            c1.download_button("📥 Download PNG", data=png, file_name="qr.png", mime="image/png", key="tab1_dl_png")
            c2.download_button("📥 Download SVG", data=svg, file_name="qr.svg", mime="image/svg+xml", key="tab1_dl_svg")
        else:
            st.warning("⚠️ Please enter text or a URL first.", icon="⚠️")

# ============================================================
# Tab 2: Single vCard
# ============================================================
with tabs[1]:
    st.subheader("Single vCard (Contact + QR)")
    st.markdown("Fill the details; the vCard will include **Website** and **MapsLink** as two URLs when provided.")

    cA, cB = st.columns(2)
    with cA:
        first = st.text_input("First Name", key="tab2_first")
        company = st.text_input("Company", key="tab2_company")
        phone = st.text_input("Phone", key="tab2_phone")
        website = st.text_input("Website", key="tab2_website")
        location = st.text_input("Location (Address)", key="tab2_location")
    with cB:
        last = st.text_input("Last Name", key="tab2_last")
        position = st.text_input("Position", key="tab2_position")
        email = st.text_input("Email", key="tab2_email")
        mapslink = st.text_input("Google Maps Link (optional)", key="tab2_mapslink")
        dept = st.text_input("Department (optional)", key="tab2_dept")
    notes = st.text_area("Notes (optional)", key="tab2_notes")

    if st.button("Generate vCard & QR", key="tab2_generate"):
        emp = {
            "FirstName": first, "LastName": last,
            "Company": company, "Position": position,
            "Department": dept,
            "Phone": phone, "Email": email,
            "Website": website, "Location": location,
            "MapsLink": mapslink, "Notes": notes
        }
        vcard = create_vcard(emp)
        st.success("✅ vCard generated")
        st.download_button(
            "📥 Download vCard (.vcf)",
            data=vcard,
            file_name=f"{first}_{last}.vcf",
            mime="text/vcard",
            key="tab2_dl_vcf"
        )

        png = qr_png_bytes(vcard)
        svg = qr_svg_bytes(vcard)
        st.image(io.BytesIO(png), caption="vCard QR Code (PNG)", use_column_width=False)
        d1, d2 = st.columns(2)
        d1.download_button("📥 Download QR (PNG)", data=png, file_name=f"{first}_{last}.png",
                           mime="image/png", key="tab2_dl_png")
        d2.download_button("📥 Download QR (SVG)", data=svg, file_name=f"{first}_{last}.svg",
                           mime="image/svg+xml", key="tab2_dl_svg")

# ============================================================
# Tab 3: Batch QR Codes (non-vCard)
# ============================================================
with tabs[2]:
    st.subheader("Batch QR Codes (Plain, from Excel)")
    st.markdown("**Template required columns:** `Label`, `Data`")
    st.markdown("The template includes one sample row: **Website → https://alraedah.sa**")

    # Sample preview
    sample_qr_df = pd.DataFrame([{"Label": "Website", "Data": "https://alraedah.sa"}])
    st.write("👀 Sample row preview:")
    st.dataframe(sample_qr_df, use_container_width=True, key="tab3_sample_preview")

    st.download_button(
        "📥 Download Batch QR Template (.xlsx)",
        data=generate_batch_qr_template_xlsx(),
        file_name="Batch_QR_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="tab3_template_dl"
    )

    st.divider()
    uploaded_qr_excel = st.file_uploader("Upload Excel (Label, Data)", type=["xlsx"], key="tab3_upload")
    custom_suffix_qr = st.text_input("Optional: Custom suffix for output folder name (Batch QR)", key="tab3_suffix")

    qr_df = None
    if uploaded_qr_excel:
        qr_df = pd.read_excel(uploaded_qr_excel)
        st.success("✅ File uploaded. Preview of first 5 rows:")
        st.dataframe(qr_df.head(), use_container_width=True, key="tab3_user_preview")

        # Validate columns
        needed = ["Label", "Data"]
        missing = [c for c in needed if c not in qr_df.columns]
        if missing:
            st.error(f"⚠️ Missing required columns: {', '.join(missing)}")
            qr_df = None

    if st.button("🚀 Generate Batch Plain QR Codes", key="tab3_generate"):
        if qr_df is not None:
            batch_folder, summary = export_batch_plain_qr(qr_df, output_dir=".", custom_suffix=custom_suffix_qr)
            zip_buf = zip_directory(batch_folder)

            st.success("✅ Batch QR generation completed!")
            st.text_area("📋 Summary", summary, height=180, key="tab3_summary")
            st.download_button(
                label="📥 Download Batch QR Package (ZIP)",
                data=zip_buf,
                file_name=f"{os.path.basename(batch_folder)}.zip",
                mime="application/zip",
                key="tab3_dl_zip"
            )
        else:
            st.warning("⚠️ Please upload a valid Excel with `Label` and `Data` columns.", icon="⚠️")

# ============================================================
# Tab 4: Batch vCards (Employee Directory)
# ============================================================
with tabs[3]:
    st.subheader("Batch vCards (from Employee Excel)")
    st.markdown("**Required columns:** `FirstName`, `LastName`, `Phone`, `Email`")
    st.markdown("**Optional columns:** `Position`, `Department`, `Company`, `Website`, `Location`, `MapsLink`, `Notes`")

    uploaded_emp_excel = st.file_uploader("Upload Employee Excel (.xlsx)", type=["xlsx"], key="tab4_upload")
    custom_suffix_vc = st.text_input("Optional: Custom suffix for output folder name (Batch vCards)", key="tab4_suffix")

    emp_df = None
    if uploaded_emp_excel:
        emp_df = pd.read_excel(uploaded_emp_excel)
        st.success("✅ File uploaded. Preview of first 5 rows:")
        st.dataframe(emp_df.head(), use_container_width=True, key="tab4_user_preview")

        # Validate required columns
        required_cols = ["FirstName", "LastName", "Phone", "Email"]
        missing_cols = [c for c in required_cols if c not in emp_df.columns]
        if missing_cols:
            st.error(f"⚠️ Missing required columns: {', '.join(missing_cols)}")
            emp_df = None

    if st.button("🚀 Generate Batch vCards + QR", key="tab4_generate"):
        if emp_df is not None:
            batch_folder, summary = export_batch_vcards(emp_df, output_dir=".", custom_suffix=custom_suffix_vc)
            zip_buf = zip_directory(batch_folder)

            st.success("✅ Batch vCards generation completed!")
            st.text_area("📋 Summary", summary, height=180, key="tab4_summary")
            st.download_button(
                label="📥 Download Batch vCards Package (ZIP)",
                data=zip_buf,
                file_name=f"{os.path.basename(batch_folder)}.zip",
                mime="application/zip",
                key="tab4_dl_zip"
            )
        else:
            st.warning("⚠️ Please upload a valid Employee Excel with required columns.", icon="⚠️")

# ============================================================
# Tab 5: Barcodes
# ============================================================
with tabs[4]:
    st.subheader("Barcodes")
    c1, c2 = st.columns(2)
    with c1:
        bc_type = st.selectbox("Barcode Type", ["Code128", "EAN13"], key="tab5_type")
    with c2:
        bc_data = st.text_input("Barcode Data (digits only for EAN13)", key="tab5_data")

    if st.button("Generate Barcode", key="tab5_generate"):
        if bc_data.strip():
            png = generate_barcode_png(bc_data.strip(), bc_type)
            st.success("✅ Barcode generated")
            st.image(io.BytesIO(png), caption=f"{bc_type} (PNG)", use_column_width=False)
            st.download_button(
                "📥 Download Barcode (PNG)",
                data=png,
                file_name=f"{bc_type}_barcode.png",
                mime="image/png",
                key="tab5_dl_png"
            )
        else:
            st.warning("⚠️ Please enter data to encode.", icon="⚠️")

# ============================================================
# Tab 6: Employee Directory (Guide + Sample + Template)
# ============================================================
with tabs[5]:
    st.subheader("Employee Directory — Guide & Template")

    st.markdown("""
    ### 📋 How to Fill the Employee Excel
    - **Required fields** (must not be empty):
        - `FirstName`
        - `LastName`
        - `Phone`
        - `Email`
    - **Optional fields** (can be left blank, will be skipped automatically):
        - `Position`
        - `Department`
        - `Company`
        - `Website`
        - `Location` → written address (e.g., "Riyadh HQ" or full address)
        - `MapsLink` → Google Maps link (added as a second URL if filled)
        - `Notes`

    ⚡ Tip: The template includes **one sample row** (Abdurrahman Alowain).
    You can **delete or overwrite it** when adding your own employees.
    """)

    sample_emp_df = pd.DataFrame([{
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
    }])

    st.write("👀 Sample row preview:")
    st.dataframe(sample_emp_df, use_container_width=True, key="tab6_sample_preview")

    st.download_button(
        "📥 Download Employee Directory Template (.xlsx)",
        data=generate_employee_template_xlsx(),
        file_name="Employee_Directory_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="tab6_template_dl"
    )

# ============================================================
# Tab 7: Templates & Help
# ============================================================
with tabs[6]:
    st.subheader("Templates & Help")
    st.markdown("""
    #### ✅ Available Templates
    1) **Employee Directory Template** (with sample row)
       - Columns:
         `FirstName`, `LastName`, `Position`, `Department`,
         `Phone`, `Email`, `Company`, `Website`,
         `Location`, `MapsLink`, `Notes`
       - Required: `FirstName`, `LastName`, `Phone`, `Email`
       - Behavior: `Location` → vCard `ADR`; `Website` & `MapsLink` → two `URL` lines.

    2) **Batch QR Template** (with sample row)
       - Columns:
         `Label`, `Data`
       - Required: both
       - Behavior: One folder per `Label` with PNG + SVG QRs of `Data`.

    #### ℹ️ Notes
    - All batch exports include a **SUMMARY.txt** at the root.
    - SVG QR output is generated using `qrcode.image.svg` (no svgwrite dependency).
    - Zipped packages include the entire folder structure for easy distribution.
    """)

    cL, cR = st.columns(2)
    with cL:
        st.download_button(
            "📥 Download Employee Directory Template (.xlsx)",
            data=generate_employee_template_xlsx(),
            file_name="Employee_Directory_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="tab7_emp_template_dl"
        )
    with cR:
        st.download_button(
            "📥 Download Batch QR Template (.xlsx)",
            data=generate_batch_qr_template_xlsx(),
            file_name="Batch_QR_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="tab7_qr_template_dl"
        )
