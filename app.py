import streamlit as st
import pandas as pd
import sqlite3
from docx import Document
from reportlab.pdfgen import canvas
from openpyxl import Workbook
import os

st.title("Professional Invoice Generator")

# Create folders
os.makedirs("invoices", exist_ok=True)

# Database
conn = sqlite3.connect("invoice.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
invoice_no TEXT,
customer TEXT,
date TEXT,
amount REAL
)
""")

# ---------------- FORM ----------------

st.header("Create Invoice")

invoice_no = st.text_input("Invoice Number")
date = st.date_input("Invoice Date")

customer = st.text_input("Customer Name")
address = st.text_area("Customer Address")

item = st.text_input("Item Description")
qty = st.number_input("Quantity", 1)
price = st.number_input("Price", 0.0)

gst = st.number_input("GST %", 0.0)

if st.button("Generate Invoice"):

    subtotal = qty * price
    gst_amount = subtotal * gst / 100
    total = subtotal + gst_amount

    # Save History
    cursor.execute(
        "INSERT INTO invoices VALUES (?,?,?,?)",
        (invoice_no, customer, str(date), total)
    )
    conn.commit()

    # ---------------- EXCEL ----------------

    excel_file = f"invoices/{invoice_no}.xlsx"

    df = pd.DataFrame({
        "Invoice No":[invoice_no],
        "Customer":[customer],
        "Item":[item],
        "Qty":[qty],
        "Price":[price],
        "Subtotal":[subtotal],
        "GST":[gst_amount],
        "Total":[total]
    })

    df.to_excel(excel_file, index=False)

    # ---------------- WORD ----------------

    word_file = f"invoices/{invoice_no}.docx"

    doc = Document()
    doc.add_heading("TAX INVOICE", 0)

    doc.add_paragraph(f"Invoice No: {invoice_no}")
    doc.add_paragraph(f"Customer: {customer}")
    doc.add_paragraph(f"Address: {address}")

    table = doc.add_table(rows=2, cols=5)
    table.rows[0].cells[0].text = "Item"
    table.rows[0].cells[1].text = "Qty"
    table.rows[0].cells[2].text = "Price"
    table.rows[0].cells[3].text = "GST"
    table.rows[0].cells[4].text = "Total"

    table.rows[1].cells[0].text = item
    table.rows[1].cells[1].text = str(qty)
    table.rows[1].cells[2].text = str(price)
    table.rows[1].cells[3].text = str(gst_amount)
    table.rows[1].cells[4].text = str(total)

    doc.save(word_file)

    # ---------------- PDF ----------------

    pdf_file = f"invoices/{invoice_no}.pdf"

    c = canvas.Canvas(pdf_file)
    c.setFont("Helvetica", 12)

    c.drawString(200, 800, "TAX INVOICE")

    c.drawString(50, 750, f"Invoice No: {invoice_no}")
    c.drawString(50, 730, f"Customer: {customer}")
    c.drawString(50, 710, f"Item: {item}")

    c.drawString(50, 680, f"Qty: {qty}")
    c.drawString(50, 660, f"Price: {price}")

    c.drawString(50, 640, f"GST: {gst_amount}")
    c.drawString(50, 620, f"Total: {total}")

    c.save()

    st.success("Invoice Created!")

    # Download buttons

    with open(pdf_file,"rb") as f:
        st.download_button("Download PDF",f,file_name=f"{invoice_no}.pdf")

    with open(word_file,"rb") as f:
        st.download_button("Download Word",f,file_name=f"{invoice_no}.docx")

    with open(excel_file,"rb") as f:
        st.download_button("Download Excel",f,file_name=f"{invoice_no}.xlsx")

# ---------------- HISTORY ----------------

st.header("Invoice History")

df = pd.read_sql("SELECT * FROM invoices", conn)

st.dataframe(df)
