from flask import Flask, render_template, request, send_file
import os
import pandas as pd
from fpdf import FPDF

app = Flask(__name__)

# Create invoices folder if it doesn't exist
os.makedirs("invoices", exist_ok=True)

@app.route('/')
def index():
    return render_template('invoice.html')


@app.route('/generate', methods=['POST'])
def generate():
    
    data = {
        'invoice_number': request.form['invoice_number'],
        'date': request.form['date'],
        'customer_name': request.form['customer_name'],
        'customer_address': request.form['customer_address'],
        'item_desc': request.form['item_desc'],
        'quantity': int(request.form['quantity']),
        'rate': float(request.form['rate']),
        'gst': float(request.form['gst'])
    }

    # Calculations
    amount = data['quantity'] * data['rate']
    gst_amount = amount * data['gst'] / 100
    total = amount + gst_amount

    data['amount'] = amount
    data['gst_amount'] = gst_amount
    data['total'] = total

    # Save Excel
    excel_path = f"invoices/{data['invoice_number']}.xlsx"
    df = pd.DataFrame([data])
    df.to_excel(excel_path, index=False)

    # Generate PDF
    pdf_path = f"invoices/{data['invoice_number']}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="GST Invoice", ln=True, align="C")
    pdf.ln(10)

    for key, value in data.items():
        pdf.cell(200, 10, txt=f"{key.replace('_',' ').title()}: {value}", ln=True)

    pdf.output(pdf_path)

    return f"""
    <div style='text-align:center;margin-top:40px;font-family:Arial'>
        <h2>✅ Invoice Generated Successfully</h2>

        <a href='/invoices/{data['invoice_number']}.xlsx' download>
        Download Excel
        </a>

        <br><br>

        <a href='/invoices/{data['invoice_number']}.pdf' download>
        Download PDF
        </a>

        <br><br>

        <a href='/'>Create Another Invoice</a>
    </div>
    """


@app.route('/invoices/<filename>')
def download_invoice(filename):
    path = f"invoices/{filename}"
    return send_file(path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
