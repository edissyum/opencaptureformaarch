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
import queue
import sys
import tempfile
import time

# useful to use the worker and avoid ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from kuyruk import Kuyruk
from kuyruk_manager import Manager
import src.classes.Log as logClass
from src.process.Queue import run_queue
import src.classes.Locale as localeClass
import src.classes.Images as imagesClass
import src.classes.Config as configClass
import src.classes.PyTesseract as ocrClass
from src.process.OCForMaarch import process
from src.classes.Mail import move_batch_to_error
import src.classes.Separator as separatorClass
import src.classes.WebServices as webserviceClass

OCforMaarch = Kuyruk()

OCforMaarch.config.MANAGER_HOST = "127.0.0.1"
OCforMaarch.config.MANAGER_PORT = 16501
OCforMaarch.config.MANAGER_HTTP_PORT = 16500

m = Manager(OCforMaarch)


def str2bool(value):
    """
    Function to convert string to boolean

    :return: Boolean
    """
    return value.lower() in "true"


def fill_queue(
        args: dict, path: str, log: logClass.Log, separator: separatorClass.Separator, config: configClass.Config,
        image: imagesClass.Image, ocr: ocrClass.PyTesseract, locale: localeClass.Locale, web_service: webserviceClass.WebServices,
        tmp_folder: str) -> None:
    """
    Run queue to handle multiple process running at the same time

    :param args: dict or argument (path to file, process to use etc..)
    :param path: Direct path to the file
    :param log: Class Log instance
    :param separator: Class Separator instance
    :param config: Class Config instance
    :param image: Class Image instance
    :param ocr: Class OCR instance
    :param locale: Class Locale instance
    :param web_service: Class WebServices instance
    :param tmp_folder: Path to tmp folder (created using tempfile python lib)
    """
    q = queue.Queue()

    # Find file in the wanted folder (default or exported pdf after qrcode separation)
    for file in os.listdir(path):
        if check_file(image, file, config, log):
            q = process(args, path + file, log, separator, config, image, ocr, locale, web_service, tmp_folder, q)

    while not q.empty():
        run_queue(q, config, image, log, web_service, ocr)


def check_file(image: imagesClass.Image, path: str, config: configClass.Config, log: logClass.Log) -> bool:
    """
    Check integrity of file

    :param image: Class Image instance
    :param path: Path to file
    :param config: Class Config instance
    :param log: Class Log instance
    :return: Boolean to show if integrity of file is ok or not
    """
    if not image.check_file_integrity(path, config):
        log.error('The integrity of file could\'nt be verified : ' + str(path))
        return False
    else:
        return True


def recursive_delete(list_folder: list, log: logClass.Log):
    """
    Delete recusively a folder (temporary folder)

    :param list_folder: list of folder to recursively delete
    :param log: Class Log instance
    """
    for folder in list_folder:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                try:
                    os.remove(folder + '/' + file)
                except FileNotFoundError as e:
                    log.error('Unable to delete ' + folder + '/' + file + ' on temp folder: ' + str(e))
            try:
                os.rmdir(folder)
            except FileNotFoundError as e:
                log.error('Unable to delete ' + folder + ' on temp folder: ' + str(e))


def timer(start_time: time.time(), end_time: time.time()):
    """
    Show how long the process takes

    :param start_time: Time when the program start
    :param end_time: Time when all the processes are done
    :return: Difference between :start_time and :end_time
    """
    hours, rem = divmod(end_time - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)


# If needed just run "kuyruk --app src.main.OCforMaarch manager" to have web dashboard of current running worker
@OCforMaarch.task()
def launch(args):
    start = time.time()
    # Init all the necessary classes
    config = configClass.Config()
    config.load_file(args['config'])

    if args.get('isMail') is not None:
        log = logClass.Log(args['log'])
        if args['isMail'] is True:
            log.info('Process email n°' + args['cpt'] + '/' + args['nb_of_mail'] + ' with UID : ' + args['msg_uid'])
    else:
        log = logClass.Log(config.cfg['GLOBAL']['logfile'])

    tmp_folder = tempfile.mkdtemp(dir=config.cfg['GLOBAL']['tmppath'])
    filename = tempfile.NamedTemporaryFile(dir=tmp_folder).name + '.jpg'
    locale = localeClass.Locale(config)
    ocr = ocrClass.PyTesseract(locale.localeOCR, log)
    separator = separatorClass.Separator(log, config, tmp_folder)
    web_service = webserviceClass.WebServices(
        config.cfg['OCForMaarch']['host'],
        config.cfg['OCForMaarch']['user'],
        config.cfg['OCForMaarch']['password'],
        log
    )
    image = imagesClass.Images(
        filename,
        int(config.cfg['GLOBAL']['resolution']),
        int(config.cfg['GLOBAL']['compressionquality']),
        log,
        config
    )

    # Start process
    if args.get('path') is not None:
        path = args['path']
        if str2bool(separator.enabled) is True and args['process'] == 'incoming':
            for fileToSep in os.listdir(path):
                if check_file(image, path + fileToSep, config, log):
                    separator.run(path + fileToSep)
            path = separator.output_dir_pdfa if str2bool(separator.convert_to_pdfa) is True else separator.output_dir

        # Create the Queue to store files
        fill_queue(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)

    elif args.get('file') is not None:
        path = args['file']
        if check_file(image, path, config, log):
            if str2bool(separator.enabled) is True and args['process'] == 'incoming':
                separator.run(path)
                if separator.error:  # in case the file is not a pdf or no qrcode was found, process as an image
                    process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)
                else:
                    path = separator.output_dir_pdfa if str2bool(separator.convert_to_pdfa) is True else separator.output_dir

                    # Create the Queue to store files
                    fill_queue(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)
            else:
                if check_file(image, path, config, log):
                    # Process the file and send it to Maarch
                    res = process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)
                    if args.get('isMail') is not None and args.get('isMail') is True:
                        # Process the attachments of mail
                        if res:
                            res_id = res['resId']
                            if len(args['attachments']) > 0:
                                log.info('Found ' + str(len(args['attachments'])) + ' attachments')
                                for attachment in args['attachments']:
                                    res = web_service.insert_attachment_from_mail(attachment, res_id)
                                    if res:
                                        log.info('Insert attachment OK : ' + str(res))
                                        continue
                                    else:
                                        move_batch_to_error(args['batch_path'], args['error_path'])
                                        log.error('Error while inserting attachment : ' + str(res))
                            else:
                                log.info('No attachments found')
                        else:
                            move_batch_to_error(args['batch_path'], args['error_path'])
                            log.error('Error while processing e-mail : ' + str(res))

                        recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)
                        log.info('End process')

    # Empty the tmp dir to avoid residual file
    recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)

    end = time.time()
    log.info('Process end after ' + timer(start, end) + '\n')
