import streamlit as st
import pandas as pd
import sqlite3
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from docx import Document

st.set_page_config(page_title="Professional Invoice System",layout="wide")

st.title("GST Professional Invoice Generator")

os.makedirs("invoices", exist_ok=True)

# ---------------- DATABASE ----------------

conn = sqlite3.connect("invoice.db",check_same_thread=False)
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

# ---------------- SESSION STATE ----------------

for key in ["customer","contact","gstin","date","selected_invoice"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ---------------- AUTO INVOICE NUMBER ----------------

cursor.execute("SELECT MAX(invoice_no) FROM invoices")
result = cursor.fetchone()

invoice_no = 1001 if result[0] is None else int(result[0]) + 1

st.subheader(f"Invoice No: {invoice_no}")

# ---------------- COMPANY DETAILS ----------------

st.sidebar.header("Company Details")

company_name = st.sidebar.text_input(
"Company Name","SHIVKRUTI ENTERPRISES")

company_gst = st.sidebar.text_input(
"Company GSTIN","27CFKPP2024L1Z7")

company_address = st.sidebar.text_area(
"Company Address",
"HOUSE NO-301 VAJRESHWARI ROAD, AT,ZIDKE POST DIGASHI TAL.BHIWANDI, DIST.THANE"
)

# ---------------- CUSTOMER DETAILS ----------------

col1,col2 = st.columns(2)

with col1:
    date = st.date_input("Invoice Date",value=st.session_state.get("date"))

    customer = st.text_input(
    "Customer Name",
    value=st.session_state.get("customer")
    )

with col2:
    contact = st.text_input(
    "Contact",
    value=st.session_state.get("contact")
    )

    gstin = st.text_input(
    "Customer GSTIN",
    value=st.session_state.get("gstin")
    )

address = st.text_area("Customer Address")

# ---------------- ITEMS ----------------

st.subheader("Invoice Items")

items=[]

num_items=st.number_input("Number of Items",1,10,1)

for i in range(int(num_items)):

    c1,c2,c3=st.columns(3)

    with c1:
        desc=st.text_input(f"Description {i+1}")

    with c2:
        qty=st.number_input(f"Qty {i+1}",min_value=1)

    with c3:
        price=st.number_input(f"Price {i+1}",min_value=0.0)

    items.append((desc,qty,price))

transport=st.number_input("Transport Charges",0.0)

gst_rate=st.number_input("GST %",18.0)

# ---------------- CALCULATIONS ----------------

subtotal=sum(q*p for _,q,p in items)
gst_amount=subtotal*gst_rate/100
total=subtotal+gst_amount+transport

st.write("Subtotal:",subtotal)
st.write("GST:",gst_amount)
st.write("Transport:",transport)
st.write("Grand Total:",total)

# ---------------- GENERATE / UPDATE ----------------

col1,col2=st.columns(2)

with col1:

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

        st.success("Invoice Generated Successfully")

with col2:

    if st.button("Update Selected Invoice"):

        if st.session_state.selected_invoice:

            cursor.execute(
            """UPDATE invoices
            SET customer=?,contact=?,gstin=?,date=?,total=?
            WHERE invoice_no=?""",
            (customer,contact,gstin,str(date),total,
            st.session_state.selected_invoice)
            )

            conn.commit()

            st.success("Invoice Updated")

# ---------------- PROFESSIONAL HTML INVOICE PREVIEW ----------------

st.subheader("Invoice Preview")

html_invoice=f"""
<style>

.invoice-box{{
width:800px;
margin:auto;
border:1px solid #eee;
padding:30px;
font-family:Arial;
}}

.header{{
display:flex;
justify-content:space-between;
}}

.company{{
font-size:22px;
font-weight:bold;
}}

table{{
width:100%;
border-collapse:collapse;
margin-top:20px;
}}

table,th,td{{
border:1px solid #ccc;
}}

th,td{{
padding:8px;
text-align:left;
}}

.total{{
text-align:right;
font-weight:bold;
}}

</style>

<div class="invoice-box">

<div class="header">
<div>
<div class="company">{company_name}</div>
<div>{company_address}</div>
<div>GSTIN: {company_gst}</div>
</div>

<div>
<h3>INVOICE</h3>
Invoice No: {invoice_no}<br>
Date: {date}
</div>
</div>

<hr>

<b>Bill To</b><br>
{customer}<br>
{contact}<br>
GSTIN: {gstin}

<table>

<tr>
<th>Description</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>
"""

for desc,qty,price in items:

    html_invoice+=f"""
<tr>
<td>{desc}</td>
<td>{qty}</td>
<td>{price}</td>
<td>{qty*price}</td>
</tr>
"""

html_invoice+=f"""

<tr>
<td colspan="3" class="total">Subtotal</td>
<td>{subtotal}</td>
</tr>

<tr>
<td colspan="3" class="total">GST</td>
<td>{gst_amount}</td>
</tr>

<tr>
<td colspan="3" class="total">Transport</td>
<td>{transport}</td>
</tr>

<tr>
<td colspan="3" class="total">Grand Total</td>
<td>{total}</td>
</tr>

</table>
</div>
"""

st.markdown(html_invoice,unsafe_allow_html=True)

# ---------------- HISTORY ----------------

st.header("Invoice History")

df=pd.read_sql("SELECT * FROM invoices",conn)

edited=st.data_editor(df,use_container_width=True,hide_index=True)

selection=st.session_state.get("data_editor",{})

# auto detect clicked row

if "edited_rows" in selection and selection["edited_rows"]:

    row=list(selection["edited_rows"].keys())[0]

    selected=df.iloc[row]

    st.session_state.selected_invoice=selected["invoice_no"]
    st.session_state.customer=selected["customer"]
    st.session_state.contact=selected["contact"]
    st.session_state.gstin=selected["gstin"]
    st.session_state.date=pd.to_datetime(selected["date"])

    st.rerun()

# ---------------- DELETE ----------------

st.subheader("Delete Invoice")

delete_id=st.number_input("Enter Invoice No to Delete",step=1)

if st.button("Delete Invoice"):

    cursor.execute(
    "DELETE FROM invoices WHERE invoice_no=?",(delete_id,)
    )

    cursor.execute(
    "DELETE FROM invoice_items WHERE invoice_no=?",(delete_id,)
    )

    conn.commit()

    st.warning("Invoice Deleted")
