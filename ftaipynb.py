# invoice_bot.py

import streamlit as st
import pdfplumber
import pandas as pd
import json
from transformers import pipeline

# -----------------------------
# Initialize Hugging Face LLM
# -----------------------------
generator = pipeline(
    "text-generation",
    model="tiiuae/falcon-7b-instruct",  # free instruction-tuned LLM
    max_new_tokens=500
)

# -----------------------------
# Function: Extract text from PDF
# -----------------------------
def get_pdf_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

# -----------------------------
# Function: Extract structured data
# -----------------------------
def extract_invoice_data(invoice_text):
    prompt = f"""
    You are an AI that extracts invoice data for FTA validation.
    Extract the following fields in JSON format:

    - Invoice Number
    - Invoice Date
    - Supplier Name
    - Supplier TRN
    - Buyer Name
    - Buyer TRN
    - Total Amount
    - VAT Amount
    - Description
    - Quantity
    - Unit Price
    - Email
    - Phone Number
    - Address

    Invoice Text:
    {invoice_text}

    Output only valid JSON.
    """

    output = generator(prompt)[0]['generated_text']

    # Try parsing JSON safely
    try:
        data = json.loads(output)
        return data
    except:
        return {"raw_output": output}

# -----------------------------
# Function: Process multiple invoices
# -----------------------------
def process_multiple_invoices(pdf_file_list):
    all_data = pd.DataFrame()

    for pdf_file in pdf_file_list:
        raw_text = get_pdf_text(pdf_file)
        invoice_data = extract_invoice_data(raw_text)
        all_data = pd.concat([all_data, pd.DataFrame([invoice_data])], ignore_index=True)

    return all_data

# -----------------------------
# Streamlit App
# -----------------------------
def main():
    st.set_page_config(page_title="FTA Invoice Extraction Bot")
    st.title("FTA Invoice Extraction Bot 🧾")
    st.subheader("Upload multiple invoices (PDF) and extract structured data for FTA validation")

    uploaded_files = st.file_uploader(
        "Upload invoices here", type=["pdf"], accept_multiple_files=True
    )

    if st.button("Extract Data") and uploaded_files:
        with st.spinner("Extracting data..."):
            df = process_multiple_invoices(uploaded_files)
            st.write(df.head())
            
            # Download CSV
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="fta_invoices.csv",
                mime="text/csv"
            )
        st.success("Extraction complete ✅")

if __name__ == "__main__":
    main()
