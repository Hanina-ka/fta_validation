# 📄 Enhanced FTA Invoice Validator (UAE)
# Developed by Hanina Abdul Rahman & ChatGPT

import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd
import io

# --- Streamlit Page Setup ---
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.title("📑 UAE FTA Invoice Validator")
st.caption("Check if uploaded invoices comply with UAE Federal Tax Authority (FTA) guidelines.")



# --- Upload Section ---
uploaded_files = st.file_uploader("📤 Upload Invoice PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    results = []

    for pdf_file in uploaded_files:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # --- 1️⃣ Extract Key Fields ---

        # TRN (must start with 100 and have 15 digits)
        trn_match = re.search(r'\b100\d{10,12}\b', text)
        trn = trn_match.group().strip() if trn_match else None

        # Invoice Number (handles various patterns)
        invoice_number_match = re.search(
            r'(Invoice\s*(No\.?|#|Number|Ref|Reference)?[:\s-]*([A-Za-z0-9/-]+))',
            text,
            re.IGNORECASE
        )
        invoice_number = invoice_number_match.group(3).strip() if invoice_number_match else None

        # Invoice Date (varied formats)
        date_match = re.search(
            r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
            text
        )
        invoice_date = date_match.group(1) if date_match else None

        # VAT Rate (5% or 0%)
        vat_rate_match = re.search(r'\b(5|0)\s?%|\bVAT\s*Rate[:\s]*([0-9]+)%', text, re.IGNORECASE)
        vat_rate = vat_rate_match.group(1) if vat_rate_match else "N/A"

        # Total / VAT / AED
        total_match = re.search(r'(Total\s*(Amount|AED)?[:\s]*AED?\s*([\d,]+\.\d{2}|\d+))', text, re.IGNORECASE)
        vat_amount_match = re.search(r'(VAT\s*(Amount)?[:\s]*AED?\s*([\d,]+\.\d{2}|\d+))', text, re.IGNORECASE)
        total_amount = float(total_match.group(3).replace(',', '')) if total_match else None
        vat_amount = float(vat_amount_match.group(3).replace(',', '')) if vat_amount_match else None

        # --- 2️⃣ FTA Validation Logic ---

        remarks = []
        status = "Approved ✅"

        # TRN check
        if not trn or not re.match(r'^100\d{10,12}$', trn):
            remarks.append("❌ Invalid or missing TRN")
            status = "Not Approved ❌"

        # Invoice number
        if not invoice_number:
            remarks.append("❌ Missing Invoice Number")
            status = "Not Approved ❌"

        # Invoice date validity
        if invoice_date:
            try:
                inv_date = datetime.strptime(invoice_date, "%d-%m-%Y")
            except:
                try:
                    inv_date = datetime.strptime(invoice_date, "%d/%m/%Y")
                except:
                    try:
                        inv_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                    except:
                        remarks.append("⚠️ Unrecognized date format")
                        status = "Not Approved ❌"
                        inv_date = None

            if inv_date and inv_date > datetime.now():
                remarks.append("⚠️ Future Date Detected")
                status = "Not Approved ❌"
        else:
            remarks.append("❌ Missing Invoice Date")
            status = "Not Approved ❌"

        # VAT Rate
        if vat_rate not in ["5", "5%", "0", "0%"]:
            remarks.append("⚠️ VAT rate missing or invalid")
            status = "Not Approved ❌"

        # VAT Calculation
        if total_amount and vat_amount:
            expected_vat = round(total_amount * 0.05, 2)
            if abs(vat_amount - expected_vat) > 1:
                remarks.append("⚠️ VAT Mismatch (Expected ~5%)")
                status = "Not Approved ❌"
        else:
            remarks.append("⚠️ Missing total or VAT amount")

        # AED currency check
        if "AED" not in text.upper():
            remarks.append("⚠️ Currency not in AED")

        # Label check
        if "TAX INVOICE" not in text.upper():
            remarks.append("⚠️ Missing 'Tax Invoice' label")
            status = "Not Approved ❌"

        # --- 3️⃣ Store Results ---
        results.append({
            "Invoice Name": pdf_file.name,
            "Invoice Number": invoice_number or "N/A",
            "Invoice Date": invoice_date or "N/A",
            "TRN": trn or "N/A",
            "VAT Rate": vat_rate or "N/A",
            "Total (AED)": total_amount or "N/A",
            "VAT Amount (AED)": vat_amount or "N/A",
            "FTA Status": status,
            "Remarks": ', '.join(remarks) if remarks else "All checks passed ✅"
        })

    # --- 4️⃣ Display Results ---
    df = pd.DataFrame(results)
    st.success(f"✅ Processed {len(results)} invoices successfully.")
    st.dataframe(df, use_container_width=True)

    # --- 5️⃣ Download Excel ---
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button(
        label="📥 Download FTA Validation Results",
        data=excel_buffer,
        file_name="FTA_Validation_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
