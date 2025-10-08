# fta_invoice_extractor.py

import streamlit as st
import pdfplumber
import pandas as pd
import json
from transformers import pipeline
from datetime import datetime

# -----------------------------
# Hugging Face LLM for PDF extraction
# -----------------------------
hf_generator = pipeline(
    "text-generation",
    model="tiiuae/falcon-7b-instruct",
    max_new_tokens=500
)

FTA_FIELDS = [
    "Invoice Number",
    "Invoice Date",
    "Supplier Name",
    "Supplier TRN",
    "Buyer Name",
    "Buyer TRN",
    "Total Amount",
    "VAT Amount"
]

# -----------------------------
# Extract text from PDF
# -----------------------------
def get_pdf_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

# -----------------------------
# Extract structured data from invoice
# -----------------------------
def extract_invoice_data(invoice_text):
    prompt = f"""
    You are an AI that extracts invoice data for FTA validation.
    Extract the following fields in JSON format:
    {', '.join(FTA_FIELDS)}

    Invoice Text:
    {invoice_text}

    Output only valid JSON.
    """
    output = hf_generator(prompt)[0]['generated_text']
    try:
        data = json.loads(output)
        return data
    except:
        return {"raw_output": output}

# -----------------------------
# FTA Validation
# -----------------------------
def validate_fta_fields(invoice_dict):
    issues = []
    for field in FTA_FIELDS:
        if field not in invoice_dict or not invoice_dict[field]:
            issues.append(f"{field} missing")
        else:
            value = str(invoice_dict[field]).strip()
            if "TRN" in field:
                # TRN must be 15 digits
                if not value.isdigit() or len(value) != 15:
                    issues.append(f"{field} invalid (should be 15 digits)")
            elif "Date" in field:
                # Validate date format
                try:
                    datetime.strptime(value, "%d/%m/%Y")
                except:
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                    except:
                        issues.append(f"{field} invalid format")
            elif "Amount" in field:
                try:
                    if float(value) < 0:
                        issues.append(f"{field} cannot be negative")
                except:
                    issues.append(f"{field} invalid number")
    if issues:
        invoice_dict["FTA Status"] = "❌ Not Approved: " + "; ".join(issues)
    else:
        invoice_dict["FTA Status"] = "✅ Approved"
    return invoice_dict

# -----------------------------
# Process multiple PDFs
# -----------------------------
def process_multiple_invoices(pdf_file_list):
    all_data = pd.DataFrame()
    for pdf_file in pdf_file_list:
        text = get_pdf_text(pdf_file)
        data = extract_invoice_data(text)
        validated_data = validate_fta_fields(data)
        all_data = pd.concat([all_data, pd.DataFrame([validated_data])], ignore_index=True)
    return all_data

# -----------------------------
# Streamlit App
# -----------------------------
def main():
    st.set_page_config(page_title="FTA Invoice Extractor")
    st.title("FTA Invoice Extractor 🧾")
    st.subheader("Upload PDF invoices and check FTA approval")

    uploaded_pdfs = st.file_uploader("Upload PDF invoices", type=["pdf"], accept_multiple_files=True)

    if st.button("Extract & Validate PDFs") and uploaded_pdfs:
        with st.spinner("Processing invoices..."):
            df = process_multiple_invoices(uploaded_pdfs)
            st.write(df.head(20))
            
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV with FTA status", csv_data, "fta_invoices.csv", "text/csv")
        st.success("Processing complete ✅")

if __name__ == "__main__":
    main()
