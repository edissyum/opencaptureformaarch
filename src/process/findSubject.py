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

import re
from threading import Thread

class findSubject(Thread):
    def __init__(self, text):
        Thread.__init__(self, name='subjectThread')
        self.text       = text
        self.subject    = None

    def run(self):
        for _subject in re.finditer(r"[o,O]bje[c]?t\s*(:)?\s*.*", self.text):
            self.subject = re.sub(r"[o,O]bje[c]?t\s*(:)?\s*", '', _subject.group())
            break
