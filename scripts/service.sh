#!/bin/bash
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

export LD_LIBRARY_PATH=/usr/local/lib/
export MAGICK_TMPDIR=/tmp/OpenCapture/
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

kuyruk_path=$(command -v kuyruk)

cd /opt/maarch/OpenCapture/ || exit
$kuyruk_path --app src.main.OCforMaarch worker
