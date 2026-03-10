import streamlit as st
import pandas as pd
import sqlite3
from docx import Document
from reportlab.pdfgen import canvas
import os

st.title("Professional Invoice Generator")

# Create folder
os.makedirs("invoices", exist_ok=True)

# Database
conn = sqlite3.connect("invoice.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
invoice_no TEXT,
customer TEXT,
contact TEXT,
gstin TEXT,
date TEXT,
amount REAL
)
""")

# ---------------- FORM ----------------

st.header("Create Invoice")

invoice_no = st.text_input("Invoice Number")
date = st.date_input("Invoice Date")

customer = st.text_input("Customer Name")
contact = st.text_input("Contact Number")
gstin = st.text_input("GSTIN")

address = st.text_area("Customer Address")

item = st.text_input("Item Description")
qty = st.number_input("Quantity", 1)
price = st.number_input("Price", 0.0)

transport = st.number_input("Transport Rate", 0.0)

gst = st.number_input("GST %", 0.0)

# ---------------- CALCULATION ----------------

if st.button("Generate Invoice"):

    subtotal = qty * price
    gst_amount = subtotal * gst / 100
    total = subtotal + gst_amount + transport

    # Save history
    cursor.execute(
        "INSERT INTO invoices VALUES (?,?,?,?,?,?)",
        (invoice_no, customer, contact, gstin, str(date), total)
    )
    conn.commit()

    # ---------------- EXCEL ----------------

    excel_file = f"invoices/{invoice_no}.xlsx"

    df = pd.DataFrame({
        "Invoice No":[invoice_no],
        "Date":[date],
        "Customer":[customer],
        "Contact":[contact],
        "GSTIN":[gstin],
        "Address":[address],
        "Item":[item],
        "Qty":[qty],
        "Price":[price],
        "Transport":[transport],
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
    doc.add_paragraph(f"Date: {date}")

    doc.add_paragraph(f"Customer: {customer}")
    doc.add_paragraph(f"Contact: {contact}")
    doc.add_paragraph(f"GSTIN: {gstin}")
    doc.add_paragraph(f"Address: {address}")

    table = doc.add_table(rows=2, cols=6)

    headers = ["Item","Qty","Price","Transport","GST","Total"]

    for i,h in enumerate(headers):
        table.rows[0].cells[i].text = h

    values = [item,qty,price,transport,gst_amount,total]

    for i,v in enumerate(values):
        table.rows[1].cells[i].text = str(v)

    doc.save(word_file)

    # ---------------- PDF ----------------

    pdf_file = f"invoices/{invoice_no}.pdf"

    c = canvas.Canvas(pdf_file)
    c.setFont("Helvetica", 12)

    c.drawString(200,800,"TAX INVOICE")

    c.drawString(50,760,f"Invoice No: {invoice_no}")
    c.drawString(50,740,f"Date: {date}")

    c.drawString(50,710,f"Customer: {customer}")
    c.drawString(50,690,f"Contact: {contact}")
    c.drawString(50,670,f"GSTIN: {gstin}")

    c.drawString(50,640,f"Item: {item}")
    c.drawString(50,620,f"Quantity: {qty}")
    c.drawString(50,600,f"Price: {price}")

    c.drawString(50,580,f"Transport Rate: {transport}")

    c.drawString(50,550,f"GST Amount: {gst_amount}")
    c.drawString(50,530,f"Total Amount: {total}")

    c.save()

    st.success("Invoice Created Successfully!")

    # Download buttons

    with open(pdf_file,"rb") as f:
        st.download_button("Download PDF",f,file_name=f"{invoice_no}.pdf")

    with open(word_file,"rb") as f:
        st.download_button("Download Word",f,file_name=f"{invoice_no}.docx")

    with open(excel_file,"rb") as f:
        st.download_button("Download Excel",f,file_name=f"{invoice_no}.xlsx")

# ---------------- HISTORY ----------------

st.header("Invoice History")

history = pd.read_sql("SELECT * FROM invoices", conn)

st.dataframe(history)
