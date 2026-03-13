import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import date as dt_date

st.set_page_config(page_title="Professional Invoice System",layout="wide")

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

# ---------------- SIDEBAR NAVIGATION ----------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
"Select Page",
["Create Invoice","Invoice History"]
)

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

    address=st.text_area("Customer Address")

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
    st.write("Grand Total:",total)

    # ---------------- GENERATE ----------------

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,contact,gstin,date,total) VALUES (?,?,?,?,?,?)",
        (invoice_no,customer,contact,gstin,str(date),total)
        )

        conn.commit()

        st.success("Invoice Generated")

# =====================================================
# INVOICE HISTORY PAGE
# =====================================================

elif page == "Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)

    if df.empty:

        st.info("No invoices found")

    else:

        selected=st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        key="history"
        )

        if st.session_state.history:

            try:

                row_index=list(st.session_state.history["edited_rows"].keys())[0]

                row=df.iloc[row_index]

                st.session_state.selected_invoice=row["invoice_no"]
                st.session_state.customer=row["customer"]
                st.session_state.contact=row["contact"]
                st.session_state.gstin=row["gstin"]
                st.session_state.date=pd.to_datetime(row["date"]).date()

                st.success("Invoice loaded. Go to 'Create Invoice' page.")

            except:
                pass

    # ---------------- DELETE ----------------

    st.subheader("Delete Invoice")

    delete_id=st.number_input("Enter Invoice Number",step=1)

    if st.button("Delete Invoice"):

        cursor.execute(
        "DELETE FROM invoices WHERE invoice_no=?",(delete_id,)
        )

        cursor.execute(
        "DELETE FROM invoice_items WHERE invoice_no=?",(delete_id,)
        )

        conn.commit()

        st.warning("Invoice Deleted")
