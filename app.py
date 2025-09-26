import streamlit as st
import pandas as pd
import os
import io
import zipfile
import qrcode
import qrcode.image.svg
from barcode import Code128, EAN13
from barcode.writer import ImageWriter

# -------------------------
# vCard generator
# -------------------------
def create_vcard(employee):
    vcard = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{employee.get('LastName','')};{employee.get('FirstName','')};;;",
        f"FN:{employee.get('FirstName','')} {employee.get('LastName','')}",
        f"ORG:{employee.get('Company','')}",
        f"TITLE:{employee.get('Position','')}",
    ]

    if employee.get("Phone"):
        vcard.append(f"TEL;TYPE=CELL,VOICE:{employee['Phone']}")

    if employee.get("Email"):
        vcard.append(f"EMAIL;TYPE=PREF,INTERNET:{employee['Email']}")

    if employee.get("Department"):
        vcard.append(f"NOTE:Department - {employee['Department']}")

    if employee.get("Location"):
        vcard.append(f"ADR;TYPE=WORK:;;{employee['Location']}")

    if employee.get("Website"):
        vcard.append(f"URL:{employee['Website']}")

    if employee.get("MapsLink"):
        vcard.append(f"URL:{employee['MapsLink']}")

    if employee.get("Notes"):
        vcard.append(f"NOTE:{employee['Notes']}")

    vcard.append("END:VCARD")
    return "\n".join(vcard)

# -------------------------
# Excel template generator
# -------------------------
def generate_employee_template():
    columns = [
        "FirstName", "LastName", "Position", "Department",
        "Phone", "Email", "Company", "Website",
        "Location", "MapsLink", "Notes"
    ]

    sample_data = [{
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

    df = pd.DataFrame(sample_data, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Employees")
    return output.getvalue()

# -------------------------
# Batch QR export
# -------------------------
def export_batch_qr(employees, output_dir, custom_folder=None):
    today_folder = f"Batch_QR_vCards_{pd.Timestamp.today().strftime('%Y%m%d')}"
    if custom_folder:
        today_folder = f"{today_folder}_{custom_folder}"
    batch_path = os.path.join(output_dir, today_folder)
    os.makedirs(batch_path, exist_ok=True)

    count = 0
    for _, employee in employees.iterrows():
        first = str(employee.get("FirstName", "")).strip()
        last = str(employee.get("LastName", "")).strip()
        folder_name = f"{first}_{last}".replace(" ", "_") or "Employee"
        emp_path = os.path.join(batch_path, folder_name)
        os.makedirs(emp_path, exist_ok=True)

        # vCard
        vcard_content = create_vcard(employee)
        vcf_path = os.path.join(emp_path, f"{folder_name}.vcf")
        with open(vcf_path, "w", encoding="utf-8") as f:
            f.write(vcard_content)

        # QR PNG
        qr = qrcode.make(vcard_content)
        qr.save(os.path.join(emp_path, f"{folder_name}.png"))

        # QR SVG (using built-in qrcode factory)
        factory = qrcode.image.svg.SvgImage
        svg_img = qrcode.make(vcard_content, image_factory=factory)
        svg_path = os.path.join(emp_path, f"{folder_name}.svg")
        with open(svg_path, "wb") as f:
            svg_img.save(f)

        count += 1

    # Summary file
    summary = (
        f"Batch QR & vCards Export\n"
        f"Date: {pd.Timestamp.today().strftime('%Y-%m-%d %H:%M')}\n"
        f"Folder: {today_folder}\n"
        f"Total Employees Processed: {count}\n\n"
        f"Each employee folder contains:\n"
        f"- .vcf (vCard)\n"
        f"- .png (QR Code)\n"
        f"- .svg (QR Code)\n"
    )
    with open(os.path.join(batch_path, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(summary)

    return batch_path, summary

# -------------------------
# ZIP utility
# -------------------------
def zip_directory(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer

# -------------------------
# Barcode generator
# -------------------------
def generate_barcode(data, barcode_type="Code128"):
    buffer = io.BytesIO()
    if barcode_type == "Code128":
        Code128(data, writer=ImageWriter()).write(buffer)
    elif barcode_type == "EAN13":
        data = str(data).zfill(12)  # EAN13 requires 12 digits
        EAN13(data, writer=ImageWriter()).write(buffer)
    buffer.seek(0)
    return buffer

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="QR & Employee Directory App", layout="wide")
st.title("📇 QR, Barcodes & Employee Directory App")

tabs = st.tabs(["Single vCard", "Batch vCards", "Barcodes", "Employee Directory"])

# --- Single vCard ---
with tabs[0]:
    st.subheader("Generate a Single vCard")
    first = st.text_input("First Name")
    last = st.text_input("Last Name")
    company = st.text_input("Company")
    position = st.text_input("Position")
    dept = st.text_input("Department")
    phone = st.text_input("Phone")
    email = st.text_input("Email")
    website = st.text_input("Website")
    location = st.text_input("Location (Address)")
    mapslink = st.text_input("Google Maps Link (optional)")
    notes = st.text_area("Notes")

    if st.button("Generate vCard"):
        emp = {
            "FirstName": first, "LastName": last,
            "Company": company, "Position": position,
            "Department": dept,
            "Phone": phone, "Email": email,
            "Website": website, "Location": location,
            "MapsLink": mapslink, "Notes": notes
        }
        vcard_content = create_vcard(emp)

        st.download_button(
            "📥 Download vCard (.vcf)",
            data=vcard_content,
            file_name=f"{first}_{last}.vcf",
            mime="text/vcard"
        )

        qr = qrcode.make(vcard_content)
        st.image(qr, caption="vCard QR Code")

# --- Batch vCards ---
with tabs[1]:
    st.subheader("Generate Batch vCards from Excel")
    uploaded_excel = st.file_uploader("Upload Employee Excel File", type=["xlsx"])
    custom_folder = st.text_input("Optional: Custom folder name for this batch")

    employees = None
    required_cols = ["FirstName", "LastName", "Phone", "Email"]

    if uploaded_excel:
        employees = pd.read_excel(uploaded_excel)
        st.success("✅ File uploaded. Preview below:")
        st.dataframe(employees.head(), use_container_width=True)

        missing_cols = [col for col in required_cols if col not in employees.columns]
        if missing_cols:
            st.error(f"⚠️ Missing required columns: {', '.join(missing_cols)}")
            employees = None

    if st.button("🚀 Generate Batch QR Codes"):
        if employees is not None:
            batch_folder, summary = export_batch_qr(employees, output_dir=".", custom_folder=custom_folder)
            zip_buffer = zip_directory(batch_folder)

            st.success("✅ Batch generation completed!")
            st.text_area("📋 Summary", summary, height=180)

            st.download_button(
                label="📥 Download Batch QR Package (ZIP)",
                data=zip_buffer,
                file_name=f"{os.path.basename(batch_folder)}.zip",
                mime="application/zip"
            )
        else:
            st.warning("⚠️ Please upload a valid employee Excel file first (with required columns).")

# --- Barcodes ---
with tabs[2]:
    st.subheader("Generate Barcodes")
    data = st.text_input("Enter data for barcode")
    barcode_type = st.selectbox("Select barcode type", ["Code128", "EAN13"])

    if st.button("Generate Barcode"):
        if data:
            buffer = generate_barcode(data, barcode_type)
            st.image(buffer, caption=f"{barcode_type} Barcode")
            st.download_button(
                "📥 Download Barcode (PNG)",
                data=buffer,
                file_name=f"{barcode_type}_barcode.png",
                mime="image/png"
            )
        else:
            st.warning("⚠️ Please enter data for the barcode.")

# --- Employee Directory ---
with tabs[3]:
    st.subheader("Employee Directory Tools")

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

    sample_df = pd.DataFrame([{
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

    st.write("👀 Preview of the sample row in the template:")
    st.dataframe(sample_df, use_container_width=True)

    st.download_button(
        label="📥 Download Employee Excel Template",
        data=generate_employee_template(),
        file_name="Employee_Directory_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
