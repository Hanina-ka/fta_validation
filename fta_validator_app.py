# pip install streamlit pdfplumber pandas openpyxl

import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd
import tempfile

# --- Streamlit setup ---
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.image("logo.png", width=150)  # your logo in same folder
st.title("📄 UAE FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against UAE FTA rules.")

# --- File uploader ---
uploaded_files = st.file_uploader(
    "Upload Invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

# --- Clear uploaded files ---
if st.button("Clear Results"):
    uploaded_files = None
    st.experimental_rerun()

# --- Validate each uploaded invoice ---
if uploaded_files:
    results = []
    seen_invoice_numbers = set()  # for uniqueness check

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

        text_lower = text.lower()

        # --- Extract fields ---
        trn_match = re.search(r'100\d{10}', text)
        invoice_number_match = re.search(r'Invoice\s*No[:\-]?\s*(\S+)', text, re.IGNORECASE)
        invoice_date_match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
        vat_rate_match = re.search(r'\b5\s?%|\b0\s?%', text)
        total_amount_match = re.search(r'Total\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
        vat_amount_match = re.search(r'VAT\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
        supplier_match = re.search(r'Supplier\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)
        customer_match = re.search(r'Customer\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)

        # --- Assign values ---
        trn = trn_match.group() if trn_match else None
        invoice_number = invoice_number_match.group(1) if invoice_number_match else None
        invoice_date = invoice_date_match.group() if invoice_date_match else None
