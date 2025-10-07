# -*- coding: utf-8 -*-
"""fta_invoice_validation.py"""

import pdfplumber
import re
import pandas as pd
from datetime import datetime

# ✅ Function: Extract key fields and validate against FTA rules
def validate_invoice(pdf_path):
    text = ""

    # Extract text from all pages
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    # --- 🔍 Extract common fields ---
    trn_match = re.search(r'100\d{10}', text)
    invoice_number_match = re.search(r'(Invoice\s*No[:\-]?\s*\w+)', text, re.IGNORECASE)
    invoice_date_match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
    vat_rate_match = re.search(r'\b5\s?%|\b0\s?%', text)
    total_amount_match = re.search(r'Total\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    vat_amount_match = re.search(r'VAT\s*(Amount)?\s*[:=]?\s*(AED\s*)?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    supplier_match = re.search(r'Supplier\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)
    customer_match = re.search(r'Customer\s*[:\-]?\s*([A-Za-z0-9\s,&]+)', text, re.IGNORECASE)

    # --- 🧾 Assign extracted values ---
    trn = trn_match.group() if trn_match else None
    invoice_number = invoice_number_match.group(0).split()[-1] if invoice_number_match else None
    invoice_date = invoice_date_match.group() if invoice_date_match else None
    vat_rate = vat_rate_match.group().replace(" ", "") if vat_rate_match else None
    total_amount = float(total_amount_match.group(3)) if total_amount_match else None
    vat_amount = float(vat_amount_match.group(3)) if vat_amount_match else None
    supplier = supplier_match.group(1).strip() if supplier_match else None
    customer = customer_match.group(1).strip() if customer_match else None

    # --- 🧮 Determine Invoice Type ---
    invoice_type = None
    if total_amount is not None:
        invoice_type = "Simplified Tax Invoice" if total_amount < 10000 else "Full Tax Invoice"

    # --- 🧠 FTA Validation ---
    remarks = []
    status = "Approved"

    # 1️⃣ Presence of “Tax Invoice” label
    if "tax invoice" not in text.lower():
        remarks.append("Missing 'Tax Invoice' label")
        status = "Not Approved"

    # 2️⃣ Supplier TRN validation
    if not trn or not re.match(r'^100\d{10}$', trn):
        remarks.append("Invalid or missing TRN")
        status = "Not Approved"

    # 3️⃣ Invoice number presence
    if not invoice_number:
        remarks.append("Invoice number missing")
        status = "Not Approved"

    # 4️⃣ Date validation
    if not invoice_date:
        remarks.append("Invoice date missing")
        status = "Not Approved"
    else:
        try:
            inv_date = datetime.strptime(invoice_date, "%d-%m-%Y")
            if inv_date > datetime.now():
                remarks.append("Invoice date is in the future")
                status = "Not Approved"
        except ValueError:
            remarks.append("Invalid date format")
            status = "Not Approved"

    # 5️⃣ VAT calculation check
    if total_amount and vat_amount:
        expected_vat = round(total_amount * 0.05, 2)
        if abs(vat_amount - expected_vat) > 0.5:
            remarks.append(f"VAT mismatch (Expected {expected_vat}, Found {vat_amount})")
            status = "Not Approved"

    # 6️⃣ Currency compliance
    if "aed" not in text.lower():
        remarks.append("Amounts not in AED")
        status = "Not Approved"

    # 7️⃣ Reverse charge or discount checks
    if "reverse charge" in text.lower():
        remarks.append("Reverse charge mentioned")
    if "discount" in text.lower():
        remarks.append("Discount applied — ensure VAT recalculated")

    if not remarks:
        remarks = ["All mandatory FTA checks passed"]

    return {
        "File": pdf_path.split("/")[-1],
        "Invoice Type": invoice_type,
        "TRN": trn,
        "Invoice Number": invoice_number,
        "Invoice Date": invoice_date,
        "Supplier": supplier,
        "Customer": customer,
        "VAT Rate": vat_rate,
        "VAT Amount": vat_amount,
        "Total Amount": total_amount,
        "FTA Status": status,
        "Remarks": ", ".join(remarks)
    }

# ✅ Example usage
pdf_files = ["invoice1.pdf", "invoice2.pdf"]  # replace with your file paths

results = []
for pdf in pdf_files:
    results.append(validate_invoice(pdf))

df = pd.DataFrame(results)
print(df)
df.to_excel("FTA_Validated_Invoices.xlsx", index=False)
print("\n✅ Validation complete. Results saved to 'FTA_Validated_Invoices.xlsx'")
