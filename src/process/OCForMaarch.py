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
from .findDate import findDate
from .findSubject import findSubject
from .findContact import findContact

def process(args, file, Log, Separator, Config, Image, Ocr, Locale, WebService):
    Log.info('Processing file : ' + file)

    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args['RDFF']:
        fileName = os.path.basename(file)
        if Separator.divider not in fileName:
            destination = Config.cfg['OCForMaarch']['destination']
        else:
            destination = fileName.split(Separator.divider)[0]
    # Or from the destination arguments
    elif args['destination']:
        destination = args['destination']
    else:
        destination = Config.cfg['OCForMaarch']['destination']

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

    # Create the searchable PDF if necessary
    if isOcr is False:
        os.remove(Image.jpgName)
        Ocr.generate_searchable_pdf(file, Image, Config)
        fileToSend = Ocr.searchablePdf
    else:
        fileToSend = open(file, 'rb').read()

    # Find subject of document
    subjectThread   = findSubject(Ocr.text)

    # Find date of document
    dateThread      = findDate(Ocr.text, Log, Locale, Config, WebService)

    # Find mail in document and check if the contact exist in Maarch
    contactThread   = findContact(Ocr.text, Log, Config, WebService)

    # Launch all threads
    subjectThread.start()
    dateThread.start()
    contactThread.start()

    # Wait for end of threads
    subjectThread.join()
    dateThread.join()
    contactThread.join()

    # Get the returned values
    subject = subjectThread.subject
    date    = dateThread.date
    contact = contactThread.contact
    res = WebService.insert_with_args(fileToSend, Config, contact, subject, date, destination)
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