import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import date as dt_date

st.set_page_config(page_title="GST Invoice System", layout="wide")

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

conn.commit()

# ---------------- SESSION STATE ----------------

if "customer" not in st.session_state:
    st.session_state.customer=""

if "contact" not in st.session_state:
    st.session_state.contact=""

if "gstin" not in st.session_state:
    st.session_state.gstin=""

if "date" not in st.session_state:
    st.session_state.date=dt_date.today()

if "selected_invoice" not in st.session_state:
    st.session_state.selected_invoice=None

# ---------------- SIDEBAR ----------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
"Select Page",
["Create Invoice","Invoice History"]
)

# =====================================================
# FUNCTION : PROFESSIONAL INVOICE TEMPLATE
# =====================================================

def generate_invoice_html(company_name, company_address, company_gst,
invoice_no,date,customer,contact,gstin,items,
subtotal,gst_amount,transport,total):

    rows=""

    for desc,qty,price in items:

        rows += f"""
        <tr>
        <td>{desc}</td>
        <td>{qty}</td>
        <td>{price}</td>
        <td>{qty*price}</td>
        </tr>
        """

    html=f"""

<style>

.invoice-container {{
width:800px;
margin:auto;
border:1px solid #ddd;
padding:25px;
font-family:Arial;
background:white;
}}

.header {{
display:flex;
justify-content:space-between;
}}

.company {{
font-size:22px;
font-weight:bold;
}}

table {{
width:100%;
border-collapse:collapse;
margin-top:20px;
}}

table,th,td {{
border:1px solid #ccc;
}}

th,td {{
padding:8px;
text-align:left;
}}

.total-row {{
font-weight:bold;
}}

</style>

<div class="invoice-container">

<div class="header">

<div>
<div class="company">{company_name}</div>
<div>{company_address}</div>
<div>GSTIN : {company_gst}</div>
</div>

<div>
<h2>TAX INVOICE</h2>
Invoice No : {invoice_no}<br>
Date : {date}
</div>

</div>

<hr>

<b>Bill To</b><br>
{customer}<br>
Contact : {contact}<br>
GSTIN : {gstin}

<table>

<tr>
<th>Description</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

{rows}

<tr class="total-row">
<td colspan="3">Subtotal</td>
<td>{subtotal}</td>
</tr>

<tr class="total-row">
<td colspan="3">GST</td>
<td>{gst_amount}</td>
</tr>

<tr class="total-row">
<td colspan="3">Transport</td>
<td>{transport}</td>
</tr>

<tr class="total-row">
<td colspan="3">Grand Total</td>
<td>{total}</td>
</tr>

</table>

<br>

<button onclick="window.print()">Print Invoice</button>

</div>
"""

    return html


# =====================================================
# CREATE INVOICE PAGE
# =====================================================

if page == "Create Invoice":

    st.title("GST Professional Invoice Generator")

    os.makedirs("invoices",exist_ok=True)

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result=cursor.fetchone()

    invoice_no=1001 if result[0] is None else int(result[0])+1

    st.subheader(f"Invoice No : {invoice_no}")

    # ---------------- COMPANY ----------------

    st.sidebar.header("Company Details")

    company_name=st.sidebar.text_input(
    "Company Name","SHIVKRUTI ENTERPRISES")

    company_gst=st.sidebar.text_input(
    "Company GSTIN","27CFKPP2024L1Z7")

    company_address=st.sidebar.text_area(
    "Company Address",
    "HOUSE NO-301 VAJRESHWARI ROAD, BHIWANDI"
    )

    # ---------------- CUSTOMER ----------------

    col1,col2=st.columns(2)

    with col1:

        date=st.date_input(
        "Invoice Date",
        value=st.session_state.date
        )

        customer=st.text_input(
        "Customer Name",
        value=st.session_state.customer
        )

    with col2:

        contact=st.text_input(
        "Contact",
        value=st.session_state.contact
        )

        gstin=st.text_input(
        "Customer GSTIN",
        value=st.session_state.gstin
        )

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

    # ---------------- CALCULATION ----------------

    subtotal=sum(q*p for _,q,p in items)

    gst_amount=subtotal*gst_rate/100

    total=subtotal+gst_amount+transport

    st.write("Subtotal :",subtotal)
    st.write("GST :",gst_amount)
    st.write("Grand Total :",total)

    # ---------------- PREVIEW SLIDER ----------------

    st.subheader("Invoice Preview")

    preview = st.toggle("Show Invoice Preview")

    if preview:

        html=generate_invoice_html(
        company_name,
        company_address,
        company_gst,
        invoice_no,
        date,
        customer,
        contact,
        gstin,
        items,
        subtotal,
        gst_amount,
        transport,
        total
        )

        st.markdown(html,unsafe_allow_html=True)

    # ---------------- SAVE ----------------

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,contact,gstin,date,total) VALUES (?,?,?,?,?,?)",
        (invoice_no,customer,contact,gstin,str(date),total)
        )

        conn.commit()

        st.success("Invoice Created Successfully")


# =====================================================
# HISTORY PAGE
# =====================================================

elif page == "Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)

    if df.empty:

        st.info("No invoices found")

    else:

        st.dataframe(df,use_container_width=True)

        selected_invoice=st.selectbox(
        "Select Invoice",
        df["invoice_no"]
        )

        if st.button("Load Invoice"):

            row=df[df.invoice_no==selected_invoice].iloc[0]

            st.session_state.customer=row["customer"]
            st.session_state.contact=row["contact"]
            st.session_state.gstin=row["gstin"]
            st.session_state.date=pd.to_datetime(row["date"]).date()

            st.success("Invoice Loaded. Go to Create Invoice page.")

    # ---------------- DELETE ----------------

    st.subheader("Delete Invoice")

    delete_id=st.number_input("Enter Invoice Number",step=1)

    if st.button("Delete Invoice"):

        cursor.execute(
        "DELETE FROM invoices WHERE invoice_no=?",(delete_id,)
        )

        conn.commit()

        st.warning("Invoice Deleted")
