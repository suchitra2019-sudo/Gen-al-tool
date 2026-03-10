import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

st.title("GST Invoice Generator")

os.makedirs("invoices", exist_ok=True)

invoice_number = st.text_input("Invoice Number")
date = st.date_input("Date")
customer_name = st.text_input("Customer Name")
customer_address = st.text_area("Customer Address")
item_desc = st.text_input("Item Description")
quantity = st.number_input("Quantity", min_value=1)
rate = st.number_input("Rate", min_value=0.0)
gst = st.number_input("GST %", min_value=0.0)

if st.button("Generate Invoice"):

    amount = quantity * rate
    gst_amount = amount * gst / 100
    total = amount + gst_amount

    data = {
        "Invoice Number": invoice_number,
        "Date": str(date),
        "Customer Name": customer_name,
        "Customer Address": customer_address,
        "Item Description": item_desc,
        "Quantity": quantity,
        "Rate": rate,
        "GST %": gst,
        "Amount": amount,
        "GST Amount": gst_amount,
        "Total": total
    }

    df = pd.DataFrame([data])

    excel_path = f"invoices/{invoice_number}.xlsx"
    pdf_path = f"invoices/{invoice_number}.pdf"

    df.to_excel(excel_path, index=False)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="GST Invoice", ln=True, align="C")
    pdf.ln(10)

    for key, value in data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf.output(pdf_path)

    st.success("Invoice Generated Successfully!")

    with open(excel_path, "rb") as file:
        st.download_button(
            label="Download Excel",
            data=file,
            file_name=f"{invoice_number}.xlsx"
        )

    with open(pdf_path, "rb") as file:
        st.download_button(
            label="Download PDF",
            data=file,
            file_name=f"{invoice_number}.pdf"
        )
