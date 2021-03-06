#! /usr/bin/env python3
#
#	Copyright (c) 2021 code-defined.com. All rights reserved.
#	GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#

'''

File:     config.py
Type:     python3
Purpose:  Redneck Spa automation.

Author:         Mark Rogers
Date:           10-05-2021
email           admin@code-defined.com

'''

import os

class Config(object):
    SECRET_KEY = os.urandom(32)
    WTF_CSRF_SECRET_KEY = os.urandom(32)
    DEBUG = True
    UPLOAD_FOLDER = './upload'
    DOWNLOAD_FOLDER = './download'
    ALLOWED_EXTENSIONS = {'json', 'xlsx'}