# ✅ GST BILLING SOFTWARE WITH HISTORY + DELETE OPTION

import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="GST Billing Software", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("billing.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    contact TEXT,
    gstin TEXT,
    total REAL,
    date TEXT
)
""")
conn.commit()

# ---------------- SIDEBAR ----------------
menu = st.sidebar.radio("Navigation", ["Create Invoice", "Invoice History"])

# ---------------- PDF FUNCTION ----------------
def generate_pdf(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,sgst,transport,total):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer,pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    if os.path.exists(logo):
        elements.append(Image(logo,60,60))

    elements.append(Paragraph(f"<b>{company}</b>",styles['Title']))
    elements.append(Paragraph(f"{address} | GSTIN:{gst}",styles['Normal']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Invoice #{invoice_no}",styles['Normal']))
    elements.append(Paragraph(f"Date: {formatted_date}",styles['Normal']))
    elements.append(Paragraph(f"Customer: {customer}",styles['Normal']))

    elements.append(Spacer(1,20))

    data=[["Item","Qty","Rate","Total"]]
    for desc,qty,price in items:
        data.append([desc,qty,price,qty*price])

    table=Table(data)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))
    elements.append(table)

    elements.append(Spacer(1,20))
    elements.append(Paragraph(f"Total: {total}",styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------- CREATE INVOICE ----------------
if menu == "Create Invoice":

    st.title("GST Invoice Generator")

    invoice_no = st.number_input("Invoice No", 1001)
    company = st.text_input("Company")
    address = st.text_area("Address")
    gst = st.text_input("GST")
    logo = "logo.png"

    customer = st.text_input("Customer")
    contact = st.text_input("Contact")
    gstin = st.text_input("Customer GSTIN")

    invoice_date = st.date_input("Date", date.today())
    formatted_date = invoice_date.strftime("%d-%m-%Y")

    items = []
    rows = st.number_input("Items", 1, 5, 1)

    for i in range(int(rows)):
        name = st.text_input(f"Item {i+1}")
        qty = st.number_input(f"Qty {i+1}", 1, key=f"q{i}")
        price = st.number_input(f"Price {i+1}", key=f"p{i}")
        items.append((name, qty, price))

    transport = st.number_input("Transport", 0.0)

    subtotal = sum(q*p for _,q,p in items)
    GST = subtotal * 0.18
    total = subtotal + GST + transport

    st.write("Subtotal:", subtotal)
    st.write("GST:", GST)
    st.write("Total:", total)

    if st.button("Save Invoice"):
        cursor.execute("INSERT INTO invoices(customer,contact,gstin,total,date) VALUES(?,?,?,?,?)",
                       (customer, contact, gstin, total, formatted_date))
        conn.commit()
        st.success("Invoice Saved Successfully")

    if st.button("Download PDF"):
        pdf = generate_pdf(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,0,transport,total)
        st.download_button("Download", pdf, file_name="invoice.pdf")

# ---------------- INVOICE HISTORY ----------------
elif menu == "Invoice History":

    st.title("Invoice History")

    df = pd.read_sql("SELECT * FROM invoices", conn)

    if not df.empty:
        st.dataframe(df)

        st.subheader("Delete Invoice")
        delete_id = st.number_input("Enter Invoice ID to Delete", min_value=1)

        if st.button("Delete Invoice"):
            cursor.execute("DELETE FROM invoices WHERE id=?", (delete_id,))
            conn.commit()
            st.success("Invoice Deleted Successfully")
            st.experimental_rerun()
    else:
        st.info("No invoices found")
