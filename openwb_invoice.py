import sys
import yaml
import csv
import smtplib
import ssl
import urllib.request
import os
from fpdf import FPDF, HTMLMixin
from datetime import date, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dateutil.relativedelta import relativedelta

# takes the name of a configuration YAML file as an argument
# creates a dictionary from the YAML file
# if no configuration file is specified, it uses config.yml


def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'config.yml'
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    log_path = download_csv(config.get('openwb_log_url'))

    log = open_csv(log_path)

    log_cleaned = clean_log(log, config.get('rfids'))

    invoice_path = create_invoice(
        log_cleaned, config.get('price_kwh'), config.get('invoice'))

    if config.get('email').get('enabled'):
        send_invoice(invoice_path, config.get('email'))

    if config.get('clean_up_log'):
        os.remove(log_path)

    if config.get('clean_up_invoice'):
        os.remove(invoice_path)


def download_csv(openwb_url):
    today = date.today()
    prev_month = today - relativedelta(months=1)
    csvname = prev_month.strftime('%Y%m') + '.csv'

    # download log CSV and save to /logs
    urllib.request.urlretrieve(
        openwb_url + csvname, csvname)

    return csvname


def open_csv(csv_path):
    # open CSV and save to var
    with open(csv_path, newline='') as csvfile:
        data = csv.reader(csvfile)
        log = list(data)  # 2d list

    return log


def clean_log(log, rfids):
    START = 0
    END = 1
    KWH = 3
    DAUER = 5
    LADEPUNKT = 6
    RFID = 8

    # clean out irrelevant RFIDs you don't want to be invoiced
    log_cleaned = []
    for row in log:
        if len(row) > RFID and (row[RFID] in rfids or rfids.len() == 0):
            new_row = [row[START], row[END],
                       row[KWH], row[DAUER], row[LADEPUNKT]]
            log_cleaned.append(new_row)

    return log_cleaned


def create_invoice(log, price_kwh, invoice):
    sender = invoice.get('sender')
    receiver = invoice.get('receiver')

    rechnungsdatum = datetime.now().strftime('%d.%m.%Y')
    rechnungsnr = datetime.now().strftime('%Y%m%d')
    summekwh = 0
    for e in log:
        summekwh += float(e[2])
    nettobetrag = price_kwh * summekwh
    umsatzsteuer = nettobetrag * 0.19
    bruttobetrag = nettobetrag + umsatzsteuer

    class MyFPDF(FPDF, HTMLMixin):
        pass

    pdf = MyFPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', size=45)
    pdf.cell(200, 10, txt='Rechnung', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', size=10)
    pdf.cell(200, 10, txt=f"{sender.get('name')} / {sender.get('street')} / {sender.get('zip')} {sender.get('city')}",
             new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.cell(200, 5, txt=f"{receiver.get('name')} / {receiver.get('street')} / {receiver.get('zip')} {receiver.get('city')}",
             new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', size=12)
    pdf.cell(200, 10, txt='Rechnungsdatum: ' +
             rechnungsdatum, new_x='LMARGIN', new_y='NEXT')
    pdf.cell(200, 10, txt='Rechnungsnr: ' +
             rechnungsnr, new_x='LMARGIN', new_y='NEXT')

    # fill HTML table with actual values (log variable)
    tbody = ''
    for row in log:
        tbody += '<tr>'
        for item in row:
            tbody += '<td>' + item + '</td>'
        tbody += '</tr>'

    html = '''
        <table border='1' cellspacing='0' cellpadding='5' width='100%'>
        <thead>
            <tr>
            <th width='20%'>Startzeit</th>
            <th width='20%'>Endzeit</th>
            <th width='20%'>kWh</th>
            <th width='20%'>Ladedauer</th>
            <th width='20%'>Ladepunkt</th>
            </tr>
        </thead>
        <tbody>
            ''' + tbody + '''
        </tbody>
        </table>
    '''
    pdf.write_html(html)

    pdf.cell(200, 15, txt='Summe Kwh: ' + str(round(summekwh, 2)),
             new_x='LMARGIN', new_y='NEXT')
    pdf.cell(200, 15, txt='Kosten Kwh (netto): ' +
             str(price_kwh) + ' Euro', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(200, 10, txt='Nettobetrag: ' + str(round(nettobetrag, 2)) +
             ' Euro', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(200, 10, txt='Umsatzsteuer(19%): ' +
             str(round(umsatzsteuer, 2)) + ' Euro', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(200, 15, txt='Bruttobetrag: ' + str(round(bruttobetrag, 2)) +
             ' Euro', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=10)
    pdf.multi_cell(200, 10, txt=f"Steuernr: {sender.get('vat_id')} \nBankverbindung: {sender.get('iban')}",
                   new_x='LMARGIN', new_y='NEXT', align='C')

    filename = 'openwbinvoice' + rechnungsnr + '.pdf'

    pdf.output(filename)
    return filename


def send_invoice(invoice_path, email):
    # create a multipart message and set headers
    message = MIMEMultipart()
    message['From'] = email.get('sender')
    message['To'] = email.get('receiver')
    subject = email.get('subject') + ' Rechnungsnr: ' + datetime.now().strftime(
        '%Y%m%d') if email.get('include_invoice_number') else email.get('subject')
    message['Subject'] = subject
    message["Bcc"] = email.get('receiver')  # Recommended for mass emails

    # add body to email
    message.attach(MIMEText(email.get('body'), 'plain'))

    # open PDF file in binary mode
    with open(invoice_path, 'rb') as attachment:
        # add file as application/octet-stream
        # email client can usually download this automatically as attachment
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())

    # encode file in ASCII characters to send by email
    encoders.encode_base64(part)

    # add header as key/value pair to attachment part
    part.add_header(
        'Content-Disposition',
        f"attachment; filename= {invoice_path}",
    )

    # add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    # log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(email.get('smtp_server'), email.get('smtp_port'), context=context) as server:
        server.login(email.get('sender'), email.get('password'))
        server.sendmail(
            email.get('sender'), email.get('receiver'), text
        )


if __name__ == '__main__':
    main()
