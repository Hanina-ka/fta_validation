import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.title("📄 FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against UAE FTA rules.")

uploaded_files = st.file_uploader("Upload Invoice PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    results = []

    for pdf_file in uploaded_files:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # --- Extract key fields ---
        trn_match = re.search(r'\b100\d{10}\b', text)
        vat_rate_match = re.search(r'\b(?:5|5%)\b', text)
        vat_amount_match = re.search(r'VAT\s*[:=]?\s*(?:AED\s*)?(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        total_amount_match = re.search(r'Total\s*[:=]?\s*(?:AED\s*)?(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        invoice_no_match = re.search(r'(?:Invoice\s*(?:No\.?|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)', text, re.IGNORECASE)

        # --- Improved date detection ---
        date_patterns = [
            r'\b\d{2}[-/]\d{2}[-/]\d{4}\b',
            r'\b\d{4}[-/]\d{2}[-/]\d{2}\b',
            r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b',
            r'\b[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}\b'
        ]
        invoice_date = None
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                invoice_date = match.group()
                break

        # --- Clean extracted fields ---
        trn = trn_match.group() if trn_match else None
        vat_rate = vat_rate_match.group() if vat_rate_match else None
        vat_amount = float(vat_amount_match.group(1)) if vat_amount_match else None
        total_amount = float(total_amount_match.group(1)) if total_amount_match else None
        invoice_no = invoice_no_match.group(1) if invoice_no_match else None

        # --- Determine invoice type ---
        if total_amount is not None:
            invoice_type = "Tax Invoice (Full)" if total_amount >= 10000 else "Simplified Tax Invoice"
        else:
            invoice_type = "Unknown"

        # --- Validation rules ---
        remarks = []
        status = "Approved"

        if not trn:
            remarks.
