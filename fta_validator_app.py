import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.title("📄 FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against UAE FTA rules.")

# -----------------------
# FILE UPLOAD
# -----------------------
uploaded_files = st.file_uploader(
    "Upload Invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    results = []  # Initialize results list

    for pdf_file in uploaded_files:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # -----------------------
        # FTA VALIDATION
        # -----------------------

        # 1️⃣ Invoice Type
        total_amount_match = re.search(r'Total\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text)
        total_amount = float(total_amount_match.group(1)) if total_amount_match else None
        invoice_type = "Full Tax Invoice" if total_amount and total_amount >= 10000 else "Simplified Tax Invoice"

        # 2️⃣ Mandatory Fields
        trn_match = re.search(r'100\d{12}', text)  # Supplier TRN 15 digits
        invoice_number_match = re.search(r'Invoice\s*No[:\s]*([A-Za-z0-9-]+)', text)
        date_match = re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', text)
        description_match = re.search(r'Description', text, re.IGNORECASE)
        vat_rate_match = re.search(r'\b[05]\s?%', text)
        vat_amount_match = re.search(r'VAT\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text)

        trn = trn_match.group() if trn_match else None
        invoice_number = invoice_number_match.group(1) if invoice_number_match else None
        invoice_date = date_match.group() if date_match else None
        description_present = True if description_match else False
        vat_rate = vat_rate_match.group() if vat_rate_match else None
        vat_amount = float(vat_amount_match.group(1)) if vat_amount_match else None

        remarks = []
        status = "Approved"

        # Check Tax Invoice label
        if not re.search(r'Tax Invoice', text, re.IGNORECASE):
            remarks.append("Missing 'Tax Invoice' label")
            status = "Not Approved"

        # TRN check
        if not trn or not re.match(r'^100\d{12}$', trn):
            remarks.append("Invalid or missing Supplier TRN")
            status = "Not Approved"

        # Invoice number check
        if not invoice_number:
            remarks.append("Missing Invoice Number")
            status = "Not Approved"

        # Invoice date check
        if invoice_date:
            try:
                inv_date = datetime.strptime(invoice_date, "%d-%m-%Y")
                if inv_date > datetime.now():
                    remarks.append("Future date")
                    status = "Not Approved"
            except:
                remarks.append("Invalid date format")
                status = "Not Approved"
        else:
            remarks.append("Missing Invoice Date")
            status = "Not Approved"

        # Description check
        if not description_present:
            remarks.append("Missing Description of Goods/Services")
            status = "Not Approved"

        # VAT rate check
        if vat_rate not in ["5%", "5", "0%", "0"]:
            remarks.append("Incorrect VAT rate")
            status = "Not Approved"

        # VAT calculation check
        if total_amount and vat_amount is not None and vat_rate in ["5%", "5"]:
            expected_vat = round(total_amount * 0.05, 2)
            if abs(vat_amount - expected_vat) > 0.5:
                remarks.append("VAT amount mismatch")
                status = "Not Approved"

        # Currency check
        if not re.search(r'AED', text, re.IGNORECASE):
            remarks.append("Currency not in AED")
            status = "Not Approved"

        # Special cases: reverse charge / discount / tax exempt
        if re.search(r'reverse charge', text, re.IGNORECASE) and 'The recipient is required' not in text:
            remarks.append("Reverse charge wording missing")
            status = "Not Approved"

        if re.search(r'discount', text, re.IGNORECASE):
            remarks.append("Discount applied — check VAT calculation")

        if re.search(r'tax exempt|out of scope', text, re.IGNORECASE):
            remarks.append("Tax exempt / out of scope wording present — verify compliance")

        # Store result
        results.append({
            "Invoice Name": pdf_file.name,
            "Invoice Type": invoice_type,
            "Supplier TRN": trn,
            "Invoice Number": invoice_number,
            "Invoice Date": invoice_date,
            "Description Present": "Yes" if description_present else "No",
            "Total Amount": total_amount,
            "VAT Rate": vat_rate,
            "VAT Amount": vat_amount,
            "FTA Status": status,
            "Remarks": ', '.join(remarks) if remarks else "All checks passed"
        })

    # -----------------------
    # DISPLAY RESULTS
    # -----------------------
    df = pd.DataFrame(results)
    st.dataframe(df)

    # -----------------------
    # DOWNLOAD EXCEL
    # -----------------------
    output_file = "FTA_Validation_Results.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Results")

    with open(output_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel",
            data=f,
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
