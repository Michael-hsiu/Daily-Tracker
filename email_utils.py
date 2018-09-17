import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser

from pathlib import Path
import os
from os import listdir
from os.path import isfile, join
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.properties'))
config = dict(config.items('Setup'))

COMMASPACE = ', '

# Given a dict with times spent on certain categories, populate an email template and send it out.
def send_email_with_config(metrics_dict, graph_file_path, date, to_email):

    # Fill in email metadata
    from_email = config['from_email']
    from_pw = config['from_pw']
    to_email = to_email

    # Build email
    msg = MIMEMultipart()
    msg['Subject'] = 'Daily Breakdown Report: ' + date
    msg['From'] = from_email
    msg['To'] = COMMASPACE.join([from_email, to_email])

    # Populate email template with metrics
    html_file = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'email_template.html'), 'r', encoding='utf-8')

    print("USING_METRICS_DIST: ", metrics_dict)
    html_source_txt = html_file.read().format(**metrics_dict)
    print("FORMATTED_EMAIL: ", html_source_txt)

    msg_text = MIMEText(html_source_txt, 'html')
    msg.attach(msg_text)

    # Attach graph image to email
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), graph_file_path), 'rb') as fp:
        msg_img = MIMEImage(fp.read())
    msg_img.add_header('Content-ID', '<image1>')
    msg.attach(msg_img)

    # Send email via gmail
    smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_server.ehlo()
    smtp_server.starttls()
    smtp_server.login(from_email, from_pw)
    send_result = smtp_server.send_message(msg=msg, from_addr=from_email, to_addrs=to_email)
    smtp_server.close()

    print("EMAIL_SEND_RESULT: ", send_result)
    print('\n\n')

    return None
