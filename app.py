import streamlit as st
import pandas as pd
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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

company_name = st.sidebar.text_input("Company Name","SHIVKRUTI ENTERPRISES")

company_gst = st.sidebar.text_input("Company GSTIN","27CFKPP2024L1Z7")

company_address = st.sidebar.text_area("Company Address","HOUSE NO-301 VAJRESHWARI ROAD, AT,ZIDKE POST DIGASHI TAL.BHIWANDI, DIST.THANE")

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

    if os.path.exists("logo.png"):
        c.drawImage("logo.png",40,height-80,width=80)

    c.setFont("Helvetica-Bold",16)
    c.drawString(150,height-50,company_name)

    c.setFont("Helvetica",11)
    c.drawString(150,height-70,company_address)


    
    c.drawString(150,height-90,f"GSTIN: {company_gst}")

    c.drawString(40,height-130,f"Invoice No: {invoice_no}")
    c.drawString(40,height-150,f"Date: {date}")

    c.drawString(40,height-180,f"Bill To: {customer}")
    c.drawString(40,height-200,f"Contact: {contact}")
    c.drawString(40,height-220,f"GSTIN: {gstin}")

    y = height-260

    c.drawString(40,y,"Description")
    c.drawString(300,y,"Qty")
    c.drawString(350,y,"Price")
    c.drawString(420,y,"Total")

    y -= 20

    for desc,qty,price in items:

        line_total = qty*price

        c.drawString(40,y,str(desc))
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

# ---------------- WORD ----------------

    word_file = f"invoices/invoice_{invoice_no}.docx"

    doc = Document()

    doc.add_heading(company_name)

    doc.add_paragraph(company_address)

    doc.add_paragraph(f"GSTIN: {company_gst}")

    doc.add_heading("TAX INVOICE")

    doc.add_paragraph(f"Invoice No: {invoice_no}")
    doc.add_paragraph(f"Date: {date}")

    doc.add_paragraph(f"Customer: {customer}")

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

    df.loc["Subtotal"] = ["","","",subtotal]

    df.loc["GST"] = ["","","",gst_amount]

    df.loc["Transport"] = ["","","",transport]

    df.loc["Grand Total"] = ["","","",total]

    df.to_excel(excel_file,index=False)

    st.success("Invoice Generated Successfully")

# ---------------- DOWNLOAD ----------------

    with open(pdf_file,"rb") as f:
        st.download_button("Download PDF",f,file_name="invoice.pdf")

    with open(word_file,"rb") as f:
        st.download_button("Download Word",f,file_name="invoice.docx")

    with open(excel_file,"rb") as f:
        st.download_button("Download Excel",f,file_name="invoice.xlsx")

# ---------------- HISTORY ----------------

st.header("Invoice History")

df = pd.read_sql("SELECT * FROM invoices",conn)

st.dataframe(df)
