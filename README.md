# vCard QR Generator (Streamlit)

A simple, elegant tool to generate **vCard QR codes** (v3.0 / v4.0), with **PNG/SVG export** and optional **center logo overlay**.

## Features
- vCard **3.0 / 4.0** support (UTF‑8 safe for Arabic/English)
- Fields: Name, Organization, Title, Phones, Email, Website, Address, Notes, Time Zone
- **PNG** or **SVG** output
- **Error Correction** control (L/M/Q/H)
- **Logo overlay** in the center (PNG/JPG), with adjustable size
- Auto file naming

## Quick Start
```bash
# 1) Create & activate a virtual environment (recommended)
python3 -m venv .venv && source .venv/bin/activate   # macOS/Linux
# On Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```

Open the local URL shown in terminal (usually http://localhost:8501).

## Notes
- For large vCards or when using a logo, keep **Error Correction = H** and increase **box size** for best scan reliability.
- Most phone Contacts apps import vCard **3.0** reliably. Use **4.0** if you need the newer format.
- Embedding an actual **PHOTO** field inside the vCard often makes the QR too dense; use the center logo instead.
