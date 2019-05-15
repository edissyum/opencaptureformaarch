![Logo OpenCapture](https://vitrine.hellyum.com/wp-content/uploads/2019/04/OpenCapture.png)

# OpenCapture for Maarch  18.10

OpenCapture is a **free and Open Source** software under **GNU General Public License v3.0**.

The functionnalities of OC for Maarch are :

 - Process PDF or image file as input
 - Process files by batch (in a given folder) or single
 - Output searchable PDF, one or multi pages
 - Split PDF using QRCode and rename splitted PDF file using QRCode content
 - OCR and text recognition :
    - Find a date and use it as metadata
    - Find a mail or URL to reconciliate with an existing contact in Maarch
    - Find an object and use it as metadata
 - Insert documents in Maarch with pre-qualified metadata :
    - Destination with QRCode
    - Date, contact, object with text recognition
 - Output PDF or PDF/A file
 - Works with **fr_FR** and **en_EN** locales
 - Fully logged, infos and errors
 - For now it deals only with **PDF** or **JPG** files
 - Check integrity of a file to avoid processing incomplete files
 - Handle different process type
 - QR Code recognition from a file to reconcile it with the original document

# Installation

## Linux Distributions

Tested with :
- Ubuntu 18.10 with Python 3.7.1 & Tesseract v4.0.0
- Ubuntu Server 18.10 with Python 3.7.1 or Python 3.6.7 & Tesseract v4.0.0
- Debian 9.8 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0
- Debian 9.6 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0

## Install OpenCapture for Maarch

Nothing as simple as that :

    $ sudo mkdir /opt/maarch/ && sudo chmod -R 775 /opt/maarch/ && sudo chown -R your_user:your_group /opt/maarch/
    $ sudo apt install git
    $ git clone -b 1.0 https://gitlab.com/edissyum/opencapture/opencaptureformaarch /opt/maarch/OpenCapture/
    $ cd /opt/maarch/OpenCapture/install/

The ./Makefile command create the service, but you may want to change the User and Group so just open the ./Makefile and change lines **16** and **17**


    $ sudo ./Makefile
    $ mv /opt/maarch/OpenCapture/src/config/config.ini.default /opt/maarch/OpenCapture/src/config/config.ini

  It will install all the needed dependencies, compile and install Tesseract V4.0.0 with french and english locale. If you need more locales, just do :

    $ sudo apt install tesseract-ocr-langcode

  Here is a list of all available languages code : https://www.macports.org/ports.php?by=name&substr=tesseract-

## Set up the incron & the cron to start the service

We want to automatise the capture of document. For that, we'll use incrontab.
First, add your user into the following file :

> /etc/incron.allow

Then use <code>incrontab -e</code> and put the following line :

    /path/to/capture/ IN_CLOSE_WRITE,IN_MOVED_TO /opt/maarch/OpenCapture/scripts/launch_IN.sh $@/$#

We use worker and jobs to enqueue process. The worker is encapsulated into a service who needs to be started in order to run the process. It's needed to cron the boot of the service at every restart, by the root user :

    $ sudo crontab -e

   And add

    @reboot systemctl start oc-worker.service

### Utilisations
Here is some examples of possible usages in the launch_XX.sh script:

    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -f file.pdf -process incoming
    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/
    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename
    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename -resid 100 -chrono MAARCH/2019D/1

--read-destination-from-filename is related to separation with QR CODE. It's reading the filename, based on the **divider** option in config.ini, to find the entity ID
-f stands for unique file
-p stands for path containing PDF/JPG files and process them as batch
-process stands for process mode (incoming or outgoing. If none, incoming will be choose)


## WebServices for Maarch 18.10

In order to reconciliate a contact it's needed to contact the Maarch database. For that 2 little PHP web services were developed.
To reconciliation documents, 2 other WS were developed
First, go into your Maarch installation (e.g : **/var/www/maarch_courrier**).

The list of files needed to be modify is in install/Maarch with the correct structure. Each modifications on files are between the following tags :

    // NCH01
        some code...
    // END NCH01

Just report the modifications onto you Maarch installation

## Various
If you want to generate PDF/A instead of PDF, you have to do the following :

> cp install/sRGB_IEC61966-2-1_black_scaled.icc /usr/share/ghostscript/X.XX/
> nano +8 /usr/share/ghostscript/X.XX/lib/PDFA_def.ps
> Replace : %/ICCProfile (srgb.icc) % Customise
> By : /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize


# Informations
## QRCode separation

Maarch permit the creation of separator, with QRCODE containing the ID of an entity. "DGS" for example. If enabled is config.ini, the separation allow us to split a PDF file containing QR Code and create PDF with a filename prefixed with the entity ID. e.g : "DGS_XXXX.pdf"

## Configuration

The file <code>src/config/config.ini</code> is splitted in different categories

 - Global
    - Choose the number of threads used to multi-threads (5 by defaults)
    - Resolution and compressionQuality when PDF are converted to JPG
    - String use to sanitize char when mail detection
    - Set the default path of the project (default : **/opt/maarch/OpenCapture/**)
    - tmpPath, no need to modify
    - errorPath, no need to modify
    - Path to the logFile, no need to modify
 - Locale
    - Choose the locale for text recognition (about date format and regex), by default it's **fr_FR** or **en_EN** but you can add more (see further in the README)
    - Choose the locale of OCR (see the langcodes of Tesseract)
    - Path for the locale JSON file for date (related to the first option of Locale), no need to modify
 - Regex
    - Add extensions to detect URL during text detection
 - Separator_QR
    - Enable or disable
    - Choose to export PDF or PDF/A
    - Path to export PDF or PDF/A, no need to modify
    - Tmp path, no need to modify
    - Modify the default divider if needed (eg. DGS_XXX.pdf or DGS-XXX.pdf)
  - OCForMaarch
    - Link to **/rest** API of Maarch with User and Password
  - OCForMaarch_**process_name**
     - Default metadata to insert documents (type_id, status, typist, priority, format, category_id and destination)

## Apache modifications

In case some big files would be sent, you have to increase the **post_max_size** parameter on the following file
> /etc/php/7.X/apache2/php.ini

By default it is recommended to replace **8M** by **20M** or more if needed

# LICENSE

OpenCapture for Maarch is released under the GPL v3.
