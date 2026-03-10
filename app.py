import streamlit as st
import pandas as pd
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

st.set_page_config(page_title="Invoice Generator")

st.title("Professional Invoice Generator")

# Create invoice folder
os.makedirs("invoices", exist_ok=True)

# ---------------- DATABASE ----------------

conn = sqlite3.connect("invoice.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,
customer TEXT,
contact TEXT,
gstin TEXT,
date TEXT,
total REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoice_items(
invoice_no INTEGER,
description TEXT,
qty INTEGER,
price REAL
)
""")

conn.commit()

# ---------------- AUTO INVOICE NUMBER ----------------

cursor.execute("SELECT MAX(invoice_no) FROM invoices")
result = cursor.fetchone()

if result is None or result[0] is None:
    invoice_no = 1001
else:
    invoice_no = int(result[0]) + 1

st.subheader(f"Invoice No: {invoice_no}")

# ---------------- CUSTOMER DETAILS ----------------

date = st.date_input("Invoice Date")

customer = st.text_input("Customer Name")

contact = st.text_input("Contact Number")

gstin = st.text_input("GSTIN")

address = st.text_area("Customer Address")

# ---------------- ITEMS ----------------

st.subheader("Invoice Items")

items = []

num_items = st.number_input("Number of Items",1,20,1)

for i in range(int(num_items)):

    col1,col2,col3 = st.columns(3)

    with col1:
        desc = st.text_input(f"Description {i+1}")

    with col2:
        qty = st.number_input(f"Qty {i+1}",min_value=1)

    with col3:
        price = st.number_input(f"Price {i+1}",min_value=0.0)

    items.append((desc,qty,price))

transport = st.number_input("Transport Charges",0.0)

gst_rate = st.number_input("GST %",18.0)

# ---------------- CALCULATION ----------------

subtotal = sum(q*p for _,q,p in items)

gst_amount = subtotal * gst_rate / 100

total = subtotal + gst_amount + transport

st.write("Subtotal:", subtotal)

st.write("GST Amount:", gst_amount)

st.write("Transport:", transport)

st.write("Grand Total:", total)

# ---------------- GENERATE INVOICE ----------------

if st.button("Generate Invoice"):

    try:

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,contact,gstin,date,total) VALUES (?,?,?,?,?,?)",
        (invoice_no,customer,contact,gstin,str(date),total)
        )

        for desc,qty,price in items:
            cursor.execute(
            "INSERT INTO invoice_items VALUES (?,?,?,?)",
            (invoice_no,desc,qty,price)
            )

        conn.commit()

    except Exception as e:
        st.error(f"Database Error: {e}")

    # ---------------- PDF GENERATION ----------------

    pdf_file = f"invoices/invoice_{invoice_no}.pdf"

    c = canvas.Canvas(pdf_file,pagesize=A4)

    width,height = A4

    c.setFont("Helvetica-Bold",16)
    c.drawString(230,height-50,"TAX INVOICE")

    c.setFont("Helvetica",11)

    c.drawString(50,height-100,f"Invoice No: {invoice_no}")
    c.drawString(50,height-120,f"Date: {date}")

    c.drawString(50,height-150,f"Customer: {customer}")
    c.drawString(50,height-170,f"Contact: {contact}")
    c.drawString(50,height-190,f"GSTIN: {gstin}")

    y = height-240

    c.drawString(50,y,"Description")
    c.drawString(300,y,"Qty")
    c.drawString(350,y,"Price")
    c.drawString(420,y,"Total")

    y -= 20

    for desc,qty,price in items:

        line_total = qty * price

        c.drawString(50,y,str(desc))
        c.drawString(300,y,str(qty))
        c.drawString(350,y,str(price))
        c.drawString(420,y,str(line_total))

        y -= 20

    y -= 20

    c.drawString(350,y,f"Subtotal: {subtotal}")

    y -= 20

    c.drawString(350,y,f"GST: {gst_amount}")

    y -= 20

    c.drawString(350,y,f"Transport: {transport}")

    y -= 20

    c.setFont("Helvetica-Bold",12)

    c.drawString(350,y,f"Grand Total: {total}")

    c.save()

    st.success("Invoice Generated Successfully")

    with open(pdf_file,"rb") as f:
        st.download_button("Download PDF",f,file_name=f"invoice_{invoice_no}.pdf")

# ---------------- HISTORY ----------------

st.header("Invoice History")

search = st.text_input("Search Customer")

query = "SELECT * FROM invoices"

if search:
    query += f" WHERE customer LIKE '%{search}%'"

df = pd.read_sql(query,conn)

st.dataframe(df)
