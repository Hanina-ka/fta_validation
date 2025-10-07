import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd

# Set up the app
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")
st.title("📄 FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against FTA rules.")

# Upload PDFs
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

        # --- FTA Validation ---
        trn_match = re.search(r'100\d{10}', text)
        vat_rate_match = re.search(r'\b5\s?%', text)
        vat_amount_match = re.search(r'VAT\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text)
        total_amount_match = re.search(r'Total\s*[:=]?\s*AED?\s*(\d+(\.\d{2})?)', text)
        date_match = re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', text)

        trn = trn_match.group() if trn_match else None
        vat_rate = vat_rate_match.group() if vat_rate_match else None
        vat_amount = float(vat_amount_match.group(1)) if vat_amount_match else None
        total_amount = float(total_amount_match.group(1)) if total_amount_match else None
        invoice_date = date_match.group() if date_match else None

        remarks = []
        status = "Approved"

        if not trn or not re.match(r'^100\d{10}$', trn):
            remarks.append("Invalid TRN")
            status = "Not Approved"

        if vat_rate not in ["5%", "5"]:
            remarks.append("VAT incorrect")
            status = "Not Approved"

        if vat_amount is not None and total_amount is not None:
            if abs(vat_amount - (total_amount * 0.05)) > 0.5:
                remarks.append("VAT mismatch")
                status = "Not Approved"

        if invoice_date:
            try:
                inv_date = datetime.strptime(invoice_date, "%d-%m-%Y")
                if inv_date > datetime.now():
                    remarks.append("Future date")
                    status = "Not Approved"
            except:
                remarks.append("Invalid date format")
                status = "Not Approved"

        # Store result
        results.append({
            "Invoice Name": pdf_file.name,
            "TRN": trn,
            "VAT Rate": vat_rate,
            "VAT Amount": vat_amount,
            "Total Amount": total_amount,
            "Invoice Date": invoice_date,
            "FTA Status": status,
            "Remarks": ', '.join(remarks) if remarks else 'All checks passed'
        })

    # Display results in the app
    df = pd.DataFrame(results)
    st.dataframe(df)

    # Excel download - handle properly for Streamlit
    output_file = "FTA_Validation_Results.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Results")

    # Streamlit download button
    with open(output_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel",
            data=f,
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
