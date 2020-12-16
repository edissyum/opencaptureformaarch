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
import re
import shutil

from bs4 import BeautifulSoup
import json


def process_form(args, config, config_mail, log, web_service, process_name, file):
    json_identifier = config.cfg['GLOBAL']['formpath'] + 'forms_identifier.json'

    if os.path.isfile(json_identifier):
        identifier = open(json_identifier, 'r').read()
        identifier = json.loads(identifier)
        process_found = False
        process = False
        for _process in identifier:
            subject = args['data']['subject']
            keyword_subject = identifier[_process]['keyword_subject']
            args['data']['modelId'] = identifier[_process]['model_id']
            if keyword_subject in subject:
                process_found = True
                process = _process
                log.info('The e-mail will use the "' + process + '" form process')

        # If a process is found, use the specific JSON file to search data using REGEX
        if process_found:
            json_file = config.cfg['GLOBAL']['formpath'] + identifier[process]['json_file']

            if os.path.isfile(json_file):
                data = open(json_file, 'r').read()
                data = json.loads(data)['FIELDS']
                contact_fields = data['CONTACT']['data']
                contact_table = data['CONTACT']['table']
                letterbox_fields = data['LETTERBOX']['data']

                file_content = open(args['file'], 'r')
                text_parsed = BeautifulSoup(file_content, 'html.parser')
                text = text_parsed.findAll(['p'])
                results = {
                    contact_table: {},
                }
                for line in text:
                    line = line.get_text()
                    for field in contact_fields:
                        regex = contact_fields[field]['regex']
                        column = contact_fields[field]['column']
                        res = re.findall(r'' + regex, line)
                        if res:
                            results[contact_table][column] = res[0]

                    for field in letterbox_fields:
                        regex = field['regex']
                        column = field['column']
                        regex_return = re.findall(r'' + regex, line)
                        if regex_return:
                            if column != 'custom':
                                args['data'][column] = regex_return[0]
                            # If we have a mapping specified, search for value between []
                            if 'mapping' in field:
                                mapping = field['mapping']
                                brackets = re.findall(r'\[(.*?)]', regex_return[0])
                                text_without_brackets = re.sub(r'\[(.*?)]', '', regex_return[0]).strip()
                                cpt = 0

                                for value in brackets:
                                    if cpt < len(mapping):
                                        column = mapping[cpt]['column']
                                        if mapping[cpt]['isCustom'] == 'True':
                                            args['data']['customFields'].update({column: value})
                                        else:
                                            args['data'][column] = value
                                    cpt = cpt + 1

                                # Put the rest of the text (not in brackets) into the last map (if the cpt into mapping correponds)
                                if len(brackets) + 1 == len(mapping):
                                    last_map = mapping[len(mapping) - 1]
                                    column = last_map['column']
                                    if last_map['isCustom'] == 'True':
                                        args['data']['customFields'].update({column: text_without_brackets})
                                    else:
                                        args['data'][column] = text_without_brackets

                res_contact = web_service.create_contact(results[contact_table])
                if res_contact[0]:
                    args['data']['senders'] = [{'id': res_contact[1]['id'], 'type': 'contact'}]

                res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[process_name])
                if res:
                    log.info('Insert form from EMAIL OK : ' + str(res))
                    return res
                else:
                    try:
                        shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                    except shutil.Error as e:
                        log.error('Moving file ' + file + ' error : ' + str(e))
                    return False, res

        else:
            log.error('No process was found, the mail will be processed normally')
            return False, 'default'
    else:
        log.error("Could not find JSON config file : " + json_identifier)
