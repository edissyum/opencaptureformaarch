# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import sys
import shutil
import base64
import tempfile

from socket import gaierror
from imap_tools import utils
from imaplib import IMAP4_SSL
from imap_tools import MailBox


class Mail:
    def __init__(self, host, port, login, pwd):
        self.pwd = pwd
        self.conn = None
        self.port = port
        self.host = host
        self.login = login

    def test_connection(self, ssl):
        """
        Test the connection to the IMAP server

        :param ssl: Boolean, if SSL is needed or not
        """
        try:
            self.conn = MailBox(host=self.host, port=self.port, ssl=ssl)
        except gaierror as e:
            sys.exit('IMAP Host ' + self.host + ' on port ' + self.port + ' is unreachable : ' + str(e))

        try:
            self.conn.login(self.login, self.pwd)
        except IMAP4_SSL.error as err:
            sys.exit('Error while trying to login to ' + self.host + ' using ' + self.login + '/' + self.pwd + ' as login/password : ' + str(err))

    def check_if_folder_exist(self, folder):
        """
        Check if a folder exist into the IMAP mailbox

        :param folder: Folder to check
        :return: Boolean
        """
        folders = self.conn.folder.list()
        for f in folders:
            if folder == f['name']:
                return True
        return False

    def select_folder(self, folder):
        """
        Select a folder to find mail into

        :param folder: Folder to select
        """
        self.conn.folder.set(folder)

    def retrieve_message(self):
        """
        Retrieve all the messages into the selected mailbox

        :return: list of mails
        """
        emails = []
        for mail in self.conn.fetch():
            emails.append(mail)
        return emails

    def construct_dict_before_send_to_maarch(self, msg, cfg, backup_path):
        """
        Construct a dict with all the data of a mail (body and attachments)

        :param msg: Mailbox object containing all the data of mail
        :param cfg: Config Object
        :param backup_path: Path to backup of the e-mail
        :return: dict of Args and file path
        """
        to_str = ''
        cc_str = ''
        for to in msg.to:
            to_str += to + ';'
        for cc in msg.cc:
            cc_str += cc + ';'

        if len(msg.html) == 0:
            file_format = 'txt'
            file = backup_path + '/mail_origin/body.txt'
            # file_content = open(backup_path + '/mail_origin/body.txt', 'rb').read()
        else:
            file_format = 'html'
            file = backup_path + '/mail_origin/body.html'
            # file_content = open(backup_path + '/mail_origin/body.html', 'rb').read()

        data = {
            'mail': {
                'file': file,
                'priority': cfg['priority'],
                'status': cfg['status'],
                'type_id': cfg['type_id'],
                'category_id': cfg['category_id'],
                'format': file_format,
                'typist': cfg['typist'],
                'subject': msg.subject,
                'destination': cfg['destination'],
                'doc_date': str(msg.date),
                cfg['custom_mail_from']: msg.from_[:254],  # 254 to avoid too long string (maarch custom is limited to 255 char)
                cfg['custom_mail_to']: to_str[:-1][:254],  # 254 to avoid too long string (maarch custom is limited to 255 char)
                cfg['custom_mail_cc']: cc_str[:-1][:254]   # 254 to avoid too long string (maarch custom is limited to 255 char)
            },
            'attachments': []
        }

        attachments = self.retrieve_attachment(msg)
        attachments_path = backup_path + '/attachments/'
        for pj in attachments:
            data['attachments'].append({
                'status': 'TRA',
                'collId': 'letterbox_coll',
                'table': 'res_attachments',
                'subject': pj['filename'] + pj['format'],
                'filename': pj['filename'],
                'format': pj['format'][1:],
                'file': attachments_path + pj['filename'] + pj['format'],
            })

        return data, file

    def backup_email(self, msg, backup_path):
        """
        Backup e-mail into path before send it to Maarch

        :param msg: Mail data
        :param backup_path: Backup path
        :return: Boolean
        """
        # Backup mail
        primary_mail_path = backup_path + '/mail_origin/'
        os.mkdir(primary_mail_path)

        # Start with headers
        fp = open(primary_mail_path + 'header.txt', 'w')
        for header in msg.headers:
            fp.write(header + ' : ' + msg.headers[header][0] + '\n')
        fp.close()

        # Then body
        if len(msg.html) == 0:
            fp = open(primary_mail_path + 'body.txt', 'w')
            fp.write(msg.text)
        else:
            fp = open(primary_mail_path + 'body.html', 'w')
            fp.write(msg.html)
        fp.close()

        # For safety, backup original stream retrieve from IMAP directly
        fp = open(primary_mail_path + 'orig.txt', 'w')

        for payload in msg.obj.get_payload():
            fp.write(str(payload))

        fp.close()

        # Backup attachments
        attachments = self.retrieve_attachment(msg)
        if len(attachments) > 0:
            attachment_path = backup_path + '/attachments/'
            os.mkdir(attachment_path)
            for file in attachments:
                file_path = os.path.join(attachment_path + file['filename'] + file['format'])
                if not os.path.isfile(file_path):
                    fp = open(file_path, 'wb')
                    fp.write(file['content'])
                    fp.close()
        return True

    def move_to_destination_folder(self, msg, destination, log):
        """
        Move e-mail to selected destination IMAP folder (if action is set to move)

        :param log: Log class instance
        :param msg: Mail data
        :param destination: IMAP folder destination
        :return: Boolean
        """
        try:
            self.conn.move(msg.uid, destination)
            return True
        except utils.UnexpectedCommandStatusError as e:
            log.error('Error while moving mail to ' + destination + ' folder : ' + str(e))
            sys.exit(0)

    def delete_mail(self, msg, trash_folder, log):
        """
        Move e-mail to trash IMAP folder (if action is set to delete) if specified. Else, delete it (can't be retrieved)

        :param log: Log class instance
        :param msg: Mail Data
        :param trash_folder: IMAP trash folder
        """
        try:
            if not self.check_if_folder_exist(trash_folder):
                log.info('Trash folder (' + trash_folder + ') doesnt exist, delete mail (couldn\'t be retrieve)')
                self.conn.delete(msg.uid)
            else:
                self.move_to_destination_folder(msg, trash_folder, log)
        except utils.UnexpectedCommandStatusError as e:
            log.error('Error while deleting mail : ' + str(e))
            sys.exit(0)

    @staticmethod
    def retrieve_attachment(msg):
        """
        Retrieve all attachments from a given mail

        :param msg: Mail Data
        :return: List of all the attachments for a mail
        """
        args = []
        for att in msg.attachments:
            args.append({
                'filename': os.path.splitext(att.filename)[0].replace(' ', '_'),
                'format': os.path.splitext(att.filename)[1],
                'content': att.payload,
                'mime_type': att.content_type
            })
        return args


def move_batch_to_error(batch_path, error_path):
    """
    If error in batch process, move the batch folder into error folder

    :param batch_path: Path to the actual batch
    :param error_path: path to the error path
    """
    print(batch_path)
    try:
        os.mkdir(error_path)
    except FileExistsError:
        pass

    try:
        shutil.move(batch_path, error_path)
    except (FileNotFoundError, FileExistsError):
        pass