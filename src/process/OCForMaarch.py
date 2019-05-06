# This file is part of OpenCapture.

# OpenCapture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OpenCapture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with OpenCapture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import shutil
from .FindDate import FindDate
from .FindSubject import FindSubject
from .FindContact import FindContact

def process(args, file, Log, Separator, Config, Image, Ocr, Locale, WebService, q = None):
    Log.info('Processing file : ' + file)

    # Check if the choosen process mode if available. If not take the default one
    if args['process'] in Config.cfg['OCForMaarch']['processavailable'].split(','):
        _process = 'OCForMaarch_' + args['process'].lower()
    else:
        _process = 'OCForMaarch_' + Config.cfg['OCForMaarch']['defaultprocess'].lower()

    Log.info('Using the following process : ' + _process)
    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args['RDFF']:
        fileName = os.path.basename(file)
        if Separator.divider not in fileName:
            destination = Config.cfg[_process]['destination']
        else:
            destination = fileName.split(Separator.divider)[0]
    # Or from the destination arguments
    elif args['destination']:
        destination = args['destination']
    else:
        destination = Config.cfg[_process]['destination']

    if os.path.splitext(file)[1] == '.pdf':  # Open the pdf and convert it to JPG
        Image.pdf_to_jpg(file + '[0]')

        # Check if pdf is already OCR and searchable

        checkOcr    = os.popen('pdffonts ' + file, 'r')
        tmp         = ''
        for line in checkOcr:
            tmp += line

        if len(tmp.split('\n')) > 3:
            isOcr = True
        else:
            isOcr = False
    else:  # Open the picture
        Image.open_img(file)
        isOcr = False

    # Get the OCR of the file as a string content
    Ocr.text_builder(Image.img)

    # Find subject of document
    subjectThread   = FindSubject(Ocr.text)

    # Find date of document
    dateThread      = FindDate(Ocr.text, Log, Locale)

    # Find mail in document and check if the contact exist in Maarch
    contactThread   = FindContact(Ocr.text, Log, Config, WebService)

    # Launch all threads
    dateThread.start()
    subjectThread.start()
    contactThread.start()

    # Wait for end of threads
    dateThread.join()
    subjectThread.join()
    contactThread.join()

    # Get the returned values
    date    = dateThread.date
    subject = subjectThread.subject
    contact = contactThread.contact

    # Create the searchable PDF if necessary
    if isOcr is False:
        Ocr.generate_searchable_pdf(file, Image, Config)
        fileToSend = Ocr.searchablePdf
    else:
        fileToSend = open(file, 'rb').read()

    try:
        os.remove(Image.jpgName)  # Delete the temp file used to OCR'ed the first PDF page
    except FileNotFoundError as e:
        Log.error(e)

    if q is not None:
        fileToStore = {
            'fileToSend'    : fileToSend,
            'file'          : file,
            'date'          : date,
            'subject'       : subject,
            'contact'       : contact,
            'destination'   : destination,
            'process'       : _process
        }

        q.put(fileToStore)

        return q
    else:
        res = WebService.insert_with_args(fileToSend, Config, contact, subject, date, destination, _process)
        if res:
            Log.info("Insert OK : " + res)
            try:
                os.remove(file)
            except FileNotFoundError as e:
                Log.error('Unable to delete ' + file + ' : ' + str(e))
            return True
        else:
            shutil.move(file, Config.cfg['GLOBAL']['errorpath'] + file)
            return False
