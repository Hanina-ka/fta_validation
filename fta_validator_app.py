import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd
import io

# ---- Page Setup ----
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.markdown(
    """
    <style>
    .main { background-color: #F8F9FA; }
    .stButton>button { background-color:#0d6efd; color:white; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("📄 FTA Invoice Validator")
st.write("Upload one or more invoice PDFs to validate against **UAE FTA Tax Invoice rules.**")

# ---- Upload Section ----
uploaded_files = st.file_uploader(
    "📤 Upload Invoice PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

# ---- Helper Function ----
def extract_invoice_data(text):
    data = {}

    # Clean text (remove line breaks between words)
    text_clean = re.sub(r'\s+', ' ', text)

    # --- Key Fields ---
    data['Tax Invoice Label'] = "Tax Invoice" if re.search(r'\bTax\s*Invoice\b', text_clean, re.IGNORECASE) else "Missing"

    trn_match = re.search(r'\b100\d{10}\b', text_clean)
    data['TRN'] = trn_match.group() if trn_match else None

    invoice_match = re.search(
        r'(Invoice\s*(No\.?|#|Number|Ref|Reference)?\s*[:\-]?\s*([A-Za-z0-9\/\-\_]+))',
        text_clean, re.IGNORECASE
    )
    if not invoice_match:
        invoice_match = re.search(r'(\bNo\.?\s*[:\-]?\s*([A-Za-z0-9\/\-\_]+)|#\s*([A-Za-z0-9\/\-\_]+))', text_clean, re.IGNORECASE)
    data['Invoice Number'] = next((g for g in invoice_match.groups() if g and re.search(r'[A-Za-z0-9]', g)), None) if invoice_match else None

    date_match = re.search(r'(\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b)', text_clean)
    data['Invoice Date'] = date_match.group() if date_match else None

    vat_rate_match = re.search(r'\b(5|0)\s?%', text_clean)
    data['VAT Rate'] = vat_rate_match.group() if vat_rate_match else None

    vat_amount_match = re.search(r'VAT\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text_clean, re.IGNORECASE)
    total_amount_match = re.search(r'Total\s*(Amount|Payable)?\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text_clean, re.IGNORECASE)
    data['VAT Amount'] = float(vat_amount_match.group(1)) if vat_amount_match else None
    data['Total Amount'] = float(total_amount_match.group(2)) if total_amount_match else None

    return data

# ---- Main Logic ----
if uploaded_files:
    results = []

    for pdf_file in uploaded_files:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        invoice_data = extract_invoice_data(text)

        remarks = []
        status = "Approved"

        # --- FTA Rules Check ---
        if not invoice_data['Tax Invoice Label']:
            remarks.append("Missing 'Tax Invoice' label")
            status = "Not Approved"

        if not invoice_data['TRN']:
            remarks.append("Supplier TRN missing or invalid")
            status = "Not Approved"

        if not invoice_data['Invoice Number']:
            remarks.append("Invoice number missing")
            status = "Not Approved"

        if not invoice_data['Invoice Date']:
            remarks.append("Invoice date missing")
            status = "Not Approved"

        if invoice_data['VAT Rate'] not in ['5%', '5']:
            remarks.append("VAT rate incorrect")
            status = "Not Approved"

        if invoice_data['VAT Amount'] and invoice_data['Total Amount']:
            if abs(invoice_data['VAT Amount'] - (invoice_data['Total Amount'] * 0.05)) > 0.5:
                remarks.append("VAT amount mismatch")
                status = "Not Approved"

        results.append({
            "Invoice Name": pdf_file.name,
            **invoice_data,
            "FTA Status": status,
            "Remarks": ', '.join(remarks) if remarks else "All checks passed ✅"
        })

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    # ---- Download Excel ----
    output = io.BytesIO()
    df.to_excel(output, index=False)
    st.download_button(
        label="📥 Download Excel Report",
        data=output.getvalue(),
        file_name="FTA_Validation_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---- Clear Button ----
    if st.button("🧹 Clear All Data"):
        st.session_state.clear()
        st.rerun()
