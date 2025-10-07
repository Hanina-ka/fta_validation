import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd
import uuid

# -----------------------
# PAGE SETUP & LOGO
# -----------------------
st.set_page_config(page_title="FTA Invoice Validator", layout="wide")

# Add logo - CHANGE to your logo path
st.image("logo.png", width=150)
st.title("📄 FTA Invoice Validator")
st.write("Upload one or multiple invoice PDFs to validate against FTA rules.")

# Optional CSS styling
st.markdown("""
<style>
body {background-color: #f0f2f6;}
.stButton>button {background-color: #4CAF50; color: white; font-size: 16px; margin: 5px;}
</style>
""", unsafe_allow_html=True)

# -----------------------
# SESSION STATE FOR BATCHES
# -----------------------
if 'batches' not in st.session_state:
    st.session_state.batches = {}  # {batch_id: [results_dicts]}

# -----------------------
# FTA VALIDATION FUNCTION
# -----------------------
def validate_invoice(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

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

    if vat_rate != "5%" and vat_rate != "5":
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

    return {
        "Invoice Name": pdf_file.name,
        "TRN": trn,
        "VAT Rate": vat_rate,
        "VAT Amount": vat_amount,
        "Total Amount": total_amount,
        "Invoice Date": invoice_date,
        "FTA Status": status,
        "Remarks": ', '.join(remarks) if remarks else 'All checks passed'
    }

# -----------------------
# UPLOAD SECTION
# -----------------------
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    uploaded_files = st.file_uploader("Upload Invoice PDFs", type="pdf", accept_multiple_files=True)

with col2:
    if st.button("🗑️ Clear All Batches"):
        st.session_state.batches = {}

with col3:
    def generate_csv_all(batches_dict):
        all_results = []
        for batch_id, results in batches_dict.items():
            for r in results:
                r_copy = r.copy()
                r_copy["Batch_ID"] = batch_id
                all_results.append(r_copy)
        df_all = pd.DataFrame(all_results)
        return df_all.to_csv(index=False).encode('utf-8')

    if st.session_state.batches:
        st.download_button(
            "📥 Download All Results",
            data=generate_csv_all(st.session_state.batches),
            file_name="FTA_All_Results.csv"
        )

# Process uploaded files into a new batch
if uploaded_files:
    batch_id = str(uuid.uuid4())[:8]  # unique batch ID
    batch_results = []

    for pdf_file in uploaded_files:
        result = validate_invoice(pdf_file)
        batch_results.append(result)

    st.session_state.batches[batch_id] = batch_results

# -----------------------
# DISPLAY RESULTS
# -----------------------
if st.session_state.batches:
    st.markdown("## Uploaded Batches")
    for batch_id, results in st.session_state.batches.items():
        st.markdown(f"### Batch: {batch_id}")

        df = pd.DataFrame(results)

        # Color-code FTA_Status column
        def highlight_status(val):
            color = 'green' if val == 'Approved' else 'red'
            return f'color: {color}; font-weight: bold'

        st.dataframe(df.style.applymap(highlight_status, subset=['FTA Status']))

        # Delete this batch button
        if st.button(f"Delete Batch {batch_id}"):
            st.session_state.batches.pop(batch_id, None)
            st.experimental_rerun()

        # Download this batch
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            f"📥 Download Batch {batch_id}",
            data=csv_data,
            file_name=f"batch_{batch_id}.csv"
        )
