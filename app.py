import streamlit as st
import pandas as pd
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from docx import Document
import os

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

if result[0] is None:
    invoice_no = 1001
else:
    invoice_no = int(result[0]) + 1

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

date = st.date_input("Invoice Date")

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
    (invoice_no,customer,contact,gstin,str(date),total)
    )

    for desc,qty,price in items:
        cursor.execute(
        "INSERT INTO invoice_items VALUES (?,?,?,?)",
        (invoice_no,desc,qty,price)
        )

    conn.commit()

# ---------------- PDF ----------------

    pdf_file = f"invoices/invoice_{invoice_no}.pdf"

    c = canvas.Canvas(pdf_file,pagesize=A4)

    width,height = A4

# ----- OUTER BORDER -----

    c.rect(30,30,width-60,height-60)

# ----- LOGO -----

    if os.path.exists("logo.png"):
        try:
            c.drawImage("logo.png",40,height-100,width=80,preserveAspectRatio=True)
        except:
            pass

# ----- COMPANY HEADER -----

    c.setFont("Helvetica-Bold",16)
    c.drawString(150,height-50,company_name)

    c.setFont("Helvetica",10)
    c.drawString(150,height-70,company_address)

    c.drawString(150,height-85,f"GSTIN: {company_gst}")

    c.line(40,height-110,width-40,height-110)

# ----- BILL DETAILS -----

    c.drawString(40,height-130,f"Invoice No: {invoice_no}")
    c.drawString(350,height-130,f"Date: {date}")

    c.drawString(40,height-160,f"Bill To: {customer}")
    c.drawString(40,height-180,f"Contact: {contact}")
    c.drawString(40,height-200,f"GSTIN: {gstin}")

# ---------------- TABLE ----------------

    table_data = [["Description","Qty","Price","Total"]]

    for desc,qty,price in items:
        table_data.append([
        desc,
        qty,
        price,
        qty*price
        ])

    table = Table(table_data,colWidths=[250,70,80,100])

    table.setStyle(TableStyle([

    ("BACKGROUND",(0,0),(-1,0),colors.lightblue),

    ("GRID",(0,0),(-1,-1),1,colors.black),

    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

    ("ALIGN",(1,1),(-1,-1),"CENTER")

    ]))

    table.wrapOn(c,width,height)
    table.drawOn(c,40,height-380)

# ---------------- GST SUMMARY ----------------

    gst_table = [
    ["GST Summary",""],
    ["Taxable Amount",subtotal],
    ["GST",gst_amount],
    ["Transport",transport]
    ]

    gst = Table(gst_table,colWidths=[140,100])

    gst.setStyle(TableStyle([
    ("GRID",(0,0),(-1,-1),1,colors.black),
    ("BACKGROUND",(0,0),(-1,0),colors.lightgrey)
    ]))

    gst.wrapOn(c,width,height)
    gst.drawOn(c,40,height-500)

# ---------------- TOTAL TABLE ----------------

    total_table = [
    ["Subtotal",subtotal],
    ["GST",gst_amount],
    ["Transport",transport],
    ["Grand Total",total]
    ]

    totals = Table(total_table,colWidths=[140,120])

    totals.setStyle(TableStyle([
    ("GRID",(0,0),(-1,-1),1,colors.black),
    ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold")
    ]))

    totals.wrapOn(c,width,height)
    totals.drawOn(c,350,height-500)

# ---------------- GST DECLARATION ----------------

    c.setFont("Helvetica",9)

    c.drawString(
    40,
    120,
    "GST Declaration: We declare that this invoice shows the actual price"
    )

    c.drawString(
    40,
    105,
    "of the goods described and that all particulars are true and correct."
    )

# ---------------- SIGNATURE ----------------

    c.drawString(400,100,f"For {company_name}")

    c.drawString(400,70,"Authorized Signatory")

    c.save()

# ---------------- WORD ----------------

    word_file = f"invoices/invoice_{invoice_no}.docx"

    doc = Document()

    doc.add_heading(company_name)

    doc.add_paragraph(company_address)

    doc.add_paragraph(f"GSTIN: {company_gst}")

    doc.add_heading("TAX INVOICE")

    doc.add_paragraph(f"Invoice No: {invoice_no}")

    doc.add_paragraph(f"Date: {date}")

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

# ---------------- EXCEL ----------------

    excel_file = f"invoices/invoice_{invoice_no}.xlsx"

    df = pd.DataFrame(items,columns=["Description","Qty","Price"])

    df["Total"] = df["Qty"] * df["Price"]

    totals = pd.DataFrame({
        "Description":["Subtotal","GST","Transport","Grand Total"],
        "Qty":["","","",""],
        "Price":["","","",""],
        "Total":[subtotal,gst_amount,transport,total]
    })

    df = pd.concat([df,totals])

    df.to_excel(excel_file,index=False)

# ---------------- DOWNLOAD ----------------

    st.success("Invoice Generated Successfully")

    with open(pdf_file,"rb") as f:
        st.download_button(
        "Download PDF",
        f,
        file_name=f"invoice_{invoice_no}.pdf"
        )

    with open(word_file,"rb") as f:
        st.download_button(
        "Download Word",
        f,
        file_name=f"invoice_{invoice_no}.docx"
        )

    with open(excel_file,"rb") as f:
        st.download_button(
        "Download Excel",
        f,
        file_name=f"invoice_{invoice_no}.xlsx"
        )

# ---------------- HISTORY ----------------

st.header("Invoice History")

df = pd.read_sql("SELECT * FROM invoices",conn)

st.dataframe(df)
