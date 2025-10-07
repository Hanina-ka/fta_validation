import streamlit as st
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import re
import pandas as pd
import io

# --------------------------------------------------
# 🖼️ PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(page_title="FTA Invoice Validator", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        background-color: #0078d7;
        color: white;
        border-radius: 5px;
        height: 40px;
        width: 200px;
    }
    .title {
        text-align: center;
        font-size: 30px;
        color: #1f3c88;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="title">📄 UAE FTA Invoice Validator</p>', unsafe_allow_html=True)
st.write("Upload tax invoices (PDF) to automatically validate them against UAE FTA rules.")

# --------------------------------------------------
# 🔍 TEXT EXTRACTION HELPERS
# --------------------------------------------------

def extract_text_pdfplumber(pdf_path):
    """Try extracting text and tables using pdfplumber"""
    text_data = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if page_text:
                text_data += page_text + "\n"
    return text_data.strip()

def extract_text_ocr(pdf_path):
    """Fallback OCR extraction for scanned invoices"""
    text_data = ""
    images = convert_from_path(pdf_path)
    for img in images:
        text_data += pytesseract.image_to_string(img)
    return text_data.strip()

def extract_text(pdf_file):
    """Auto-select best extraction method"""
    text = extract_text_pdfplumber(pdf_file)
    if len(text.split()) < 30:  # If text too short, use OCR
        text = extract_text_ocr(pdf_file)
    return text

# --------------------------------------------------
# ✅ FTA VALIDATION LOGIC
# --------------------------------------------------

def validate_invoice(text):
    result = {
        "Invoice Label": "❌ Missing",
        "Supplier TRN": "❌ Invalid",
        "Invoice Number": "❌ Missing",
        "Invoice Date": "❌ Missing",
        "Currency": "❌ Not AED",
        "VAT Check": "❌ Incorrect / Missing",
        "Summary": "❌ Non-Compliant"
    }

    # 1️⃣ Invoice Label
    if re.search(r'\bTax Invoice\b', text, re.IGNORECASE):
        result["Invoice Label"] = "✅ Present"

    # 2️⃣ Supplier TRN (15-digit)
    trn = re.findall(r'\b\d{15}\b', text)
    if trn:
        result["Supplier TRN"] = f"✅ {trn[0]}"

    # 3️⃣ Invoice Number
    inv_num = re.findall(r'(?:Invoice\s*No\.?|#)\s*([A-Za-z0-9\-/]+)', text, re.IGNORECASE)
    if inv_num:
        result["Invoice Number"] = f"✅ {inv_num[0]}"

    # 4️⃣ Date (YYYY-MM-DD, DD/MM/YYYY, etc.)
    date_match = re.findall(r'(\d{2,4}[/-]\d{1,2}[/-]\d{2,4})', text)
    if date_match:
        result["Invoice Date"] = f"✅ {date_match[0]}"

    # 5️⃣ Currency AED
    if re.search(r'\bAED\b|\bDhs\b|\bDirham\b', text, re.IGNORECASE):
        result["Currency"] = "✅ AED"

    # 6️⃣ VAT correctness (5% presence)
    if re.search(r'5\s?%', text):
        result["VAT Check"] = "✅ 5% Detected"

    # 7️⃣ Final Summary
    if all("✅" in val for key, val in result.items() if key != "Summary"):
        result["Summary"] = "✅ FTA Compliant"

    return result

# --------------------------------------------------
# 📂 FILE UPLOAD
# --------------------------------------------------

uploaded_files = st.file_uploader("Upload one or more PDF invoices", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    results = []
    for file in uploaded_files:
        st.write(f"📁 **Processing:** {file.name}")
        text = extract_text(file)
        validation_result = validate_invoice(text)
        validation_result["Filename"] = file.name
        results.append(validation_result)

    df = pd.DataFrame(results)

    st.subheader("🧾 Validation Results")
    st.dataframe(df)

    # Download as Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="FTA_Validation")
    st.download_button(
        label="📥 Download Excel Report",
        data=output.getvalue(),
        file_name="FTA_Validation_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Clear button
    if st.button("🗑️ Clear All"):
        st.experimental_rerun()
