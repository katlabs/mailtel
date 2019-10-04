#!/usr/bin/env python3

from __future__ import print_function
import pickle
import os.path
from datetime import date
import base64
import telegram
import config
from io import BytesIO
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Edit the config.py with your token and Chat ID.
TOKEN = config.token
CHAT_ID = config.chat_id

def main():

    # Setup from Google API docs....
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # We search for the message from USPS delivered on/after today...
    query = "from: USPSInformedDelivery@usps.gov after:{}".format(date.today())
    response = service.users().messages().list(userId='me', q=query).execute()
    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])

    # The first message returned is what we use...
    first_msg_id = messages[0]["id"]

    msg = service.users().messages().get(userId='me', id=first_msg_id).execute()

    mails = []

    for part in msg['payload']['parts']:
        if part['filename']:
            if 'data' in part['body']:
                data=part['body']['data']
            else:
                att_id=part['body']['attachmentId']
                att=service.users().messages().attachments().get(userId='me',
                                                                 messageId=first_msg_id,
                                                                 id=att_id).execute()
                data=att['data']
            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
            mails.append(file_data)

    # Send our mail images to telegram...
    bot = telegram.Bot(token=TOKEN)
    bot.sendMessage(CHAT_ID, "{} letter(s) arriving today in the mail...".format(len(mails)))
    i = 0
    for mail in mails:
        i = i+1
        bio = BytesIO()
        bio.write(mail)
        bio.name = "mail{}.jpeg".format(i)
        bio.seek(0)
        bot.send_photo(CHAT_ID, photo=bio, caption="Letter #{}".format(i))

if __name__ == '__main__':
    main()
