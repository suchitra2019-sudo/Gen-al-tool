import streamlit as st
import pandas as pd
import sqlite3
import pdfkit
from docx import Document
import os
from datetime import date

st.set_page_config(page_title="Professional Invoice System")

st.title("GST Professional Invoice Generator")

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

invoice_no = 1001 if result[0] is None else result[0] + 1

st.subheader(f"Invoice No: {invoice_no}")

# ---------------- COMPANY DETAILS ----------------

st.sidebar.header("Company Details")

company_name = st.sidebar.text_input(
"Company Name","SHIVKRUTI ENTERPRISES"
)

company_gst = st.sidebar.text_input(
"Company GSTIN","27CFKPP2024L1Z7"
)

company_address = st.sidebar.text_area(
"Company Address",
"HOUSE NO-301 VAJRESHWARI ROAD, AT,ZIDKE POST DIGASHI TAL.BHIWANDI, DIST.THANE"
)

# ---------------- CUSTOMER DETAILS ----------------

invoice_date = st.date_input("Invoice Date",date.today())

customer = st.text_input("Customer Name")

contact = st.text_input("Contact Number")

gstin = st.text_input("Customer GSTIN")

address = st.text_area("Customer Address")

# ---------------- ITEMS ----------------

st.subheader("Invoice Items")

items = []

num_items = st.number_input("Number of Items",1,10,1)

for i in range(int(num_items)):

    col1,col2,col3 = st.columns(3)

    with col1:
        desc = st.text_input(f"Description {i+1}")

    with col2:
        qty = st.number_input(f"Qty {i+1}",min_value=1)

    with col3:
        price = st.number_input(f"Price {i+1}",min_value=0.0)

    if desc != "":
        items.append((desc,qty,price))

transport = st.number_input("Transport Charges",0.0)

gst_rate = st.number_input("GST %",18.0)

# ---------------- CALCULATIONS ----------------

subtotal = sum(q*p for _,q,p in items)

gst_amount = subtotal * gst_rate / 100

total = subtotal + gst_amount + transport

st.write("Subtotal:",subtotal)
st.write("GST:",gst_amount)
st.write("Transport:",transport)
st.write("Grand Total:",total)

# ---------------- GENERATE INVOICE ----------------

if st.button("Generate Invoice"):

    cursor.execute(
    "INSERT INTO invoices (invoice_no,customer,contact,gstin,date,total) VALUES (?,?,?,?,?,?)",
    (invoice_no,customer,contact,gstin,str(invoice_date),total)
    )

    for desc,qty,price in items:
        cursor.execute(
        "INSERT INTO invoice_items VALUES (?,?,?,?)",
        (invoice_no,desc,qty,price)
        )

    conn.commit()

# ---------------- HTML TABLE ----------------

    rows = ""

    for desc,qty,price in items:

        line_total = qty*price

        rows += f"""
        <tr>
        <td>{desc}</td>
        <td>{qty}</td>
        <td>{price}</td>
        <td>{line_total}</td>
        </tr>
        """

# ---------------- LOAD HTML TEMPLATE ----------------

    with open("templates/invoice_template.html") as f:
        html = f.read()

    html = html.replace("{{company_name}}",company_name)
    html = html.replace("{{company_address}}",company_address)
    html = html.replace("{{company_gst}}",company_gst)

    html = html.replace("{{invoice_no}}",str(invoice_no))
    html = html.replace("{{date}}",str(invoice_date))

    html = html.replace("{{customer}}",customer)
    html = html.replace("{{contact}}",contact)
    html = html.replace("{{gstin}}",gstin)

    html = html.replace("{{items}}",rows)

    html = html.replace("{{subtotal}}",str(subtotal))
    html = html.replace("{{gst}}",str(gst_amount))
    html = html.replace("{{transport}}",str(transport))
    html = html.replace("{{total}}",str(total))

# ---------------- GENERATE PDF ----------------

    pdf_file = f"invoices/invoice_{invoice_no}.pdf"

    pdfkit.from_string(html,pdf_file)

# ---------------- WORD ----------------

    word_file = f"invoices/invoice_{invoice_no}.docx"

    doc = Document()

    doc.add_heading(company_name)
    doc.add_paragraph(company_address)
    doc.add_paragraph(f"GSTIN: {company_gst}")

    doc.add_heading("TAX INVOICE")

    doc.add_paragraph(f"Invoice No: {invoice_no}")
    doc.add_paragraph(f"Date: {invoice_date}")

    table = doc.add_table(rows=1,cols=4)

    headers = ["Description","Qty","Price","Total"]

    for i,h in enumerate(headers):
        table.rows[0].cells[i].text = h

    for desc,qty,price in items:

        row = table.add_row().cells

        row[0].text = str(desc)
        row[1].text = str(qty)
        row[2].text = str(price)
        row[3].text = str(qty*price)

    doc.add_paragraph(f"Grand Total: {total}")

    doc.save(word_file)

# ---------------- DOWNLOAD ----------------

    st.success("Invoice Generated Successfully")

    with open(pdf_file,"rb") as f:
        st.download_button("Download PDF",f,file_name=f"invoice_{invoice_no}.pdf")

    with open(word_file,"rb") as f:
        st.download_button("Download Word",f,file_name=f"invoice_{invoice_no}.docx")

# ---------------- HISTORY ----------------

st.header("Invoice History")

df = pd.read_sql("SELECT * FROM invoices",conn)

st.dataframe(df)
