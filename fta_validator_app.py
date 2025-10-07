import streamlit as st
import pandas as pd
from unstructured.partition.pdf import partition_pdf
import re
import tempfile
import os

# ---------- Function to extract key details ----------
def extract_invoice_details(pdf_path):
    elements = partition_pdf(filename=pdf_path)
    text = "\n".join([str(el) for el in elements])

    # --- Pattern checks ---
    trn_match = re.search(r"\b\d{15}\b", text)
    invoice_no = re.search(r"(Invoice\s*Number|Inv\s*No\.?|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    date_match = re.search(r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})", text)
    vat_match = re.search(r"VAT\s*[:\-]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
    total_match = re.search(r"Total\s*(Amount|Payable|AED)?\s*[:\-]?\s*(AED)?\s*(\d+\.?\d*)", text, re.IGNORECASE)
    currency_match = "AED" if "AED" in text.upper() else "Other"

    # --- Invoice Type ---
    invoice_type = "Tax Invoice" if "TAX INVOICE" in text.upper() else "Simplified Invoice" if "SIMPLIFIED" in text.upper() else "Unknown"

    data = {
        "Invoice Type": invoice_type,
        "Supplier TRN": trn_match.group() if trn_match else None,
        "Invoice Number": invoice_no.group(2) if invoice_no else None,
        "Invoice Date": date_match.group(1) if date_match else None,
        "VAT Amount": vat_match.group(1) if vat_match else None,
        "Total Amount": total_match.group(3) if total_match else None,
        "Currency": currency_match
    }

    return data


# ---------- Streamlit App ----------
st.title("📄 UAE FTA Invoice Extractor (Phase 1)")

uploaded_files = st.file_uploader("Upload Invoice PDFs", accept_multiple_files=True, type=["pdf"])

if uploaded_files:
    results = []

    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        extracted_data = extract_invoice_details(tmp_path)
        extracted_data["File Name"] = uploaded_file.name
        results.append(extracted_data)

        os.remove(tmp_path)

    df = pd.DataFrame(results)
    st.dataframe(df)

    # Download button for Excel
    excel_path = "invoice_extracted_results.xlsx"
    df.to_excel(excel_path, index=False)
    with open(excel_path, "rb") as f:
        st.download_button("⬇️ Download Excel", f, file_name=excel_path)

