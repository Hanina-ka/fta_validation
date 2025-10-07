# pip install streamlit pdfplumber pandas openpyxl

import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd
import tempfile

# --- Streamlit page setup ---
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.image("logo.png", width=150)  # add your logo in the same folder
st.title("📄 FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against UAE FTA rules.")

# --- File uploader ---
uploaded_files = st.file_uploader(
    "Upload Invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

# --- Clear uploaded files option ---
if st.button("Clear Results"):
    uploaded_files = None
    st.experimental_rerun()

# --- Process uploaded files ---
if uploaded_files:
    results = []

    for uploaded_file in uploaded_files:
        # Save uploaded file to a temporary file for pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # --- FTA extraction ---
        trn_match = re.search(r'100\d{10}', text)
        invoice_number_match = re.search(r'(Invoice\s*No[:\-]?\s*\w+)', text, re.IGNORECASE)
        invoice_date_match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
        vat_rate_match = re.search(r'\b5\s?%|\b0\s?%', text)
        total_amount_match = re.search(r'Total\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
        vat_amount_match = re.search(r'VAT\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
        supplier_match = re.search(r'Supplier\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)
        customer_match = re.search(r'Customer\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)

        # --- Assign extracted values ---
        trn = trn_match.group() if trn_match else None
        invoice_number = invoice_number_match.group(0).split()[-1] if invoice_number_match else None
        invoice_date = invoice_date_match.group() if invoice_date_match else None
        vat_rate = vat_rate_match.group().replace(" ", "") if vat_rate_match else None
        total_amount = float(total_amount_match.group(3)) if total_amount_match else None
        vat_amount = float(vat_amount_match.group(3)) if vat_amount_match else None
        supplier = supplier_match.group(1).strip() if supplier_match else None
        customer = customer_match.group(1).strip() if customer_match else None

        # --- Determine invoice type ---
        invoice_type = None
        if total_amount is not None:
            invoice_type = "Simplified Tax Invoice" if total_amount < 10000 else "Full Tax Invoice"

        # --- FTA Validation ---
        remarks = []
        status = "Approved"

        if "tax invoice" not in text.lower():
            remarks.append("Missing 'Tax Invoice' label")
            status = "Not Approved"

        if not trn or not re.match(r'^100\d{10}$', trn):
            remarks.append("Invalid or missing TRN")
            status = "Not Approved"

        if not invoice_number:
            remarks.append("Invoice number missing")
            status = "Not Approved"

        if not invoice_date:
            remarks.append("Invoice date missing")
            status = "Not Approved"
        else:
            try:
                inv_date = datetime.strptime(invoice_date, "%d-%m-%Y")
                if inv_date > datetime.now():
                    remarks.append("Invoice date is in the future")
                    status = "Not Approved"
            except ValueError:
                remarks.append("Invalid date format")
                status = "Not Approved"

        if total_amount and vat_amount:
            expected_vat = round(total_amount * 0.05, 2)
            if abs(vat_amount - expected_vat) > 0.5:
                remarks.append(f"VAT mismatch (Expected {expected_vat}, Found {vat_amount})")
                status = "Not Approved"

        if "aed" not in text.lower():
            remarks.append("Amounts not in AED")
            status = "Not Approved"

        if "reverse charge" in text.lower():
            remarks.append("Reverse charge mentioned")
        if "discount" in text.lower():
            remarks.append("Discount applied — ensure VAT recalculated")

        if not remarks:
            remarks = ["All mandatory FTA checks passed"]

        results.append({
            "File": uploaded_file.name,
            "Invoice Type": invoice_type,
            "TRN": trn,
            "Invoice Number": invoice_number,
            "Invoice Date": invoice_date,
            "Supplier": supplier,
            "Customer": customer,
            "VAT Rate": vat_rate,
            "VAT Amount": vat_amount,
            "Total Amount": total_amount,
            "FTA Status": status,
            "Remarks": ", ".join(remarks)
        })

    # --- Display results ---
    df = pd.DataFrame(results)
    st.dataframe(df)

    # --- Download Excel ---
    output_file = "FTA_Validation_Results.xlsx"
    df.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel",
            data=f,
            file_name=output_file
        )
