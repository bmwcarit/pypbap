# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Common tools and attributes for pbap client and server"""

FILTER_ATTR_DICT = {
    0: ('VERSION', 'vCard Version'),
    1: ('FN', 'Formatted Name'),
    2: ('N', 'Structured Presentation of Name'),
    3: ('PHOTO', 'Associated Image or Photo'),
    4: ('BDAY', 'Birthday'),
    5: ('ADR', 'Delivery Address'),
    6: ('LABEL', 'Delivery'),
    7: ('TEL', 'Telephone Number'),
    8: ('EMAIL', 'Electronic Mail Address'),
    9: ('MAILER', 'Electronic Mail'),
    10: ('TZ', 'Time Zone'),
    11: ('GEO', 'Geographic Position'),
    12: ('TITLE', 'Job'),
    13: ('ROLE', 'Role within the Organization'),
    14: ('LOGO', 'Organization Logo'),
    15: ('AGENT', 'vCard of Person Representing'),
    16: ('ORG', 'Name of Organization'),
    17: ('NOTE', 'Comments'),
    18: ('REV', 'Revision'),
    19: ('SOUND', 'Pronunciation of Name'),
    20: ('URL', 'Uniform Resource Locator'),
    21: ('UID', 'Unique ID'),
    22: ('KEY', 'Public Encryption Key'),
    23: ('NICKNAME', 'Nickname'),
    24: ('CATEGORIES', 'Categories'),
    25: ('PROID', 'Product ID'),
    26: ('CLASS', 'Class information'),
    27: ('SORT', 'STRING String used for sorting operations'),
    28: ('X-IRMC-CALL-DATETIME', 'Time stamp'),
    # 29: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 30: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 31: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 32: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 33: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 34: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 35: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 36: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 37: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 38: ('RESERVED_FUTURE_USE', 'Reserved for future use'),
    # 39: ('PROPRIETARY_FILTER', 'Indicates the usage of a proprietary filter'),
    # 40: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 41: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 42: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 43: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 44: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 45: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 46: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 47: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 48: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 49: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 50: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 51: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 52: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 53: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 54: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 55: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 56: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 57: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 58: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 59: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 60: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 61: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 62: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage'),
    # 63: ('RESERVED_PROPRIETARY_FILTER', 'Reserved for proprietary filter usage')
}

POSSIBLE_VCARD_ATTR = ["VERSION", "FN", "N", "PHOTO", "BDAY", "ADR", "LABEL", "TEL",
                       "EMAIL", "MAILER", "TZ", "GEO", "TITLE", "ROLE", "LOGO",
                       "AGENT", "ORG", "NOTE", "REV", "SOUND", "URL", "UID", "KEY",
                       "NICKNAME", "CATEGORIES", "PROID", "CLASS", "SORT", "X-IRMC-CALL-DATETIME"]

# vcard_format: bitmask for mandatory attributes
# vcard 2.1 are VERSION ,N and TEL
# vcard 3.0 are VERSION, N, FN and TEL
MANDATORY_ATTR_BITMASK = {
    "2.1": int("10000101", 2),
    "3.0": int("10000111", 2)
}
