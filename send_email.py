import httplib2
import os
import oauth2client
from oauth2client import client, tools, file
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import mimetypes
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from stat import S_ISREG, ST_CTIME, ST_MODE
import os, sys, time
from datetime import datetime
import base64
import cv2

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Send Email'


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gmail-python-email-send.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def SendMessage(sender, to, subject, msgHtml, msgPlain, attachmentFile=None):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    if attachmentFile:
        message1 = createMessageWithAttachment(sender, to, subject, msgHtml, msgPlain, attachmentFile)
    else:
        message1 = CreateMessageHtml(sender, to, subject, msgHtml, msgPlain)
    result = SendMessageInternal(service, "me", message1)
    return result


def encode_image(image):
    encoded_string = ''
    with open(image, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode("utf-8")

    return encoded_string

def encode_image_buffer(buffer):
    encoded_string = base64.b64encode(buffer)
    return  encoded_string.decode("utf-8")
    return encoded_string

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)
        return "Error"
    return "OK"


def getDirInfo(dirpath):
    # get all entries in the directory w/ stats
    entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath))
    entries = ((os.stat(path).st_mtime, path) for path in entries)

    return entries


def renderDirInfo(entries):
    html = "<!DOCTYPE html><html><head><style>table, th, td {  border: 1px solid black;  border-collapse: collapse;}</style></head><body>"

    image_hash = {}
    hash_dir = {}
    min_val = 1e10
    max_val = 0
    for entry in entries:
        if min_val > entry[0]:
            min_val = entry[0]
        if max_val < entry[0]:
            max_val = entry[0]
        hash_dir[entry[1]] = entry[0]

    limit_recent = max_val - 24 * 3600

    elements = []
    prev_v = min_val
    for k, v in sorted(hash_dir.items(), key=lambda item: item[1]):
        element = {}
        element['file'] = k
        element['date'] = v
        element['order'] = v - prev_v
        prev_v = v
        elements.append(element)

    prev_v = elements[-1]['date']
    for i in reversed(range(len(elements) - 1)):
        val1 = elements[i]['order']
        v = elements[i]['date']
        val2 = prev_v - v
        if val2 < val1:
            elements[i]['order'] = val2
        prev_v = v

    num = 123456700

    html += "<h2>Most recent</h2><table><tr><th>File</th><th>time</th><th>duration</th></tr>"
    for element in reversed(elements):
        encoded_text = ""
        if element['date'] >= limit_recent:
            color = 'white'
            if element['order'] < 20:
                color = '#A52A2A'
                if 'jpg' in element['file']:
                    image = cv2.imread(element['file'])
                    image = cv2.resize(image, (150, 150))
                    image_name = element['file'][:-4] + '_resized.jpg'
                    cv2.imwrite(image_name, image)
                    cid = '<%d>' % (num)
                    image_hash[cid] = image_name
                    # retval, buffer = cv2.imencode('.jpg', image)
                    # encoded_text = encode_image_buffer(buffer)
                    # encoded_text = "<img src=\"data:image/jpeg;base64,%s\"/>" % (encoded_text)
                    encoded_text = "<img src=\"cid:%d\"/>" % (num)
                    num += 1
                    # encoded_text = "<img src=\"cid:computer_vision_logo.jpg\"/>"

            html += "<tr>"
            html += "<td>" + element['file'] + "</td>"
            date_str = datetime.fromtimestamp(element['date']).strftime("%A, %B %d, %H:%M:%S")
            html += "<td style = \"background-color:%s\">%s</td>" % (color, date_str)
            html += "<td style = \"background-color:%s\">%.2f</td>" % (color, element['order'])
            html += "<td>%s</td>" % (encoded_text)
            html += "</tr>"
    html += "</table><br><br>"

    html += "<h2>Remaining values</h2><table><tr><th>File</th><th>time</th><th>duration</th></tr>"
    for element in reversed(elements):
        encoded_text = ""
        if element['date'] < limit_recent:
            color = 'white'
            if element['order'] < 20:
                color = '#A52A2A'


            elif element['order'] < 200:
                color = '#CC8A8A'

            html += "<tr>"
            html += "<td>" + element['file'] + "</td>"
            date_str = datetime.fromtimestamp(element['date']).strftime("%A, %B %d, %H:%M:%S")
            html += "<td style = \"background-color:%s\">%s</td>" % (color, date_str)
            html += "<td style = \"background-color:%s\">%.2f</td>" % (color, element['order'])
            html += "</tr>"
    html += "</table></body></html>"

    return html, image_hash


def CreateMessageHtml(sender, to, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    return {'raw': base64.urlsafe_b64encode(msg.as_string().encode()).decode()}
    # return {'raw': base64.urlsafe_b64encode(msg.as_string())}


def createMessageWithAttachment(
        sender, to, subject, msgHtml, msgPlain, attachmentFiles):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      msgHtml: Html message to be sent
      msgPlain: Alternative plain text message for older email clients
      attachmentFile: The path to the file to be attached.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEMultipart('mixed')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    messageA = MIMEMultipart('alternative')
    messageR = MIMEMultipart('related')

    messageR.attach(MIMEText(msgHtml, 'html'))
    messageA.attach(MIMEText(msgPlain, 'plain'))
    messageA.attach(messageR)

    message.attach(messageA)

    for element in attachmentFiles:

        attachmentFile = attachmentFiles[element]

        print("create_message_with_attachment: file: %s" % attachmentFile)
        content_type, encoding = mimetypes.guess_type(attachmentFile)

        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)
        if main_type == 'text':
            fp = open(attachmentFile, 'rb')
            msg = MIMEText(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == 'image':
            fp = open(attachmentFile, 'rb')
            msg = MIMEImage(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == 'audio':
            fp = open(attachmentFile, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=sub_type)
            fp.close()
        else:
            fp = open(attachmentFile, 'rb')
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(fp.read())
            fp.close()
        filename = os.path.basename(attachmentFile)
        # msg.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.add_header('Content-Disposition', 'inline', filename=filename)
        msg.add_header('Content-ID', element)
        message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def createMessageWithSingleAttachment(
        sender, to, subject, msgHtml, msgPlain, attachmentFile):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      msgHtml: Html message to be sent
      msgPlain: Alternative plain text message for older email clients
      attachmentFile: The path to the file to be attached.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEMultipart('mixed')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    messageA = MIMEMultipart('alternative')
    messageR = MIMEMultipart('related')

    messageR.attach(MIMEText(msgHtml, 'html'))
    messageA.attach(MIMEText(msgPlain, 'plain'))
    messageA.attach(messageR)

    message.attach(messageA)

    print("create_message_with_attachment: file: %s" % attachmentFile)
    content_type, encoding = mimetypes.guess_type(attachmentFile)

    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    if main_type == 'text':
        fp = open(attachmentFile, 'rb')
        msg = MIMEText(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'image':
        fp = open(attachmentFile, 'rb')
        msg = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'audio':
        fp = open(attachmentFile, 'rb')
        msg = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(attachmentFile, 'rb')
        msg = MIMEBase(main_type, sub_type)
        msg.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(attachmentFile)
    # msg.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.add_header('Content-Disposition', 'inline', filename=filename)
    msg.add_header('Content-ID', '<0123456789>')
    message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def main():
    to = "ephevos@gmail.com"
    sender = "ephevos@gmail.com"
    subject = "PicTimes"
    msgHtml = "Hi<br/>Html Email"
    msgPlain = "Hi\nPlain Email"

    # msgHtml, image_hash = renderDirInfo(getDirInfo('.'))
    msgHtml, image_hash = renderDirInfo(getDirInfo('/home/pi/usb/out_pics'))
    # with open('test.html', 'w') as writer:
    #     writer.write(msgHtml)

    # SendMessage(sender, to, subject, msgHtml, msgPlain)
    # Send message with attachment:
    SendMessage(sender, to, subject, msgHtml, msgPlain, image_hash)


    for element in image_hash:
        attachmentFile = image_hash[element]
        os.remove(attachmentFile)

if __name__ == '__main__':
    main()
