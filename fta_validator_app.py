import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re

st.title("📄 FTA Invoice Validator")

# Function to extract text from PDF
def extract_text_from_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text("text")
    return text

# Function to validate invoice fields
def validate_invoice(text):
    errors = []

    # 1️⃣ Check invoice type
    if "Tax Invoice" in text:
        invoice_type = "Tax Invoice"
    elif "Simplified Tax Invoice" in text:
        invoice_type = "Simplified Tax Invoice"
    else:
        invoice_type = "Unknown"
        errors.append("Invoice type not found")

    # 2️⃣ Supplier TRN check (15 digits)
    trn_match = re.search(r"\b\d{15}\b", text)
    if not trn_match:
        errors.append("Missing or invalid Supplier TRN (must be 15 digits)")

    # 3️⃣ Currency check
    if "AED" not in text:
        errors.append("Currency not in AED")

    # 4️⃣ Mandatory fields
    mandatory_keywords = ["Invoice Number", "Date", "Supplier", "Customer", "Description", "Amount"]
    for key in mandatory_keywords:
        if key.lower() not in text.lower():
            errors.append(f"Missing mandatory field: {key}")

    return {
        "Invoice Type": invoice_type,
        "TRN": trn_match.group(0) if trn_match else None,
        "Currency": "AED" if "AED" in text else "Other",
        "Errors": ", ".join(errors) if errors else "No issues found ✅"
    }

# File upload
uploaded_file = st.file_uploader("Upload PDF Invoice", type=["pdf"])

if uploaded_file:
    st.info("Reading invoice...")
    text = extract_text_from_pdf(uploaded_file)
    
    # Validate
    result = validate_invoice(text)
    df = pd.DataFrame([result])

    st.subheader("✅ Validation Result")
    st.dataframe(df)

    # Download Excel
    st.download_button(
        label="📥 Download Validation Result (Excel)",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="fta_validation_result.csv",
        mime="text/csv"
    )
