# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Phone Book Access Profile headers"""

from PyOBEX.headers import *
from pbapcommon import FILTER_ATTR_DICT


# Application Parameters Header Properties
class AppParamProperty(object):
    def __init__(self, data, encoded=False):
        if encoded:
            self.data = data
        else:
            self.data = self.encode(data)

    def encode(self, data):
        if self.__class__.__name__ == "SearchValue":
            self.length = len(data)
        return struct.pack(">BB", self.tagid, self.length) + data

    def decode(self):
        return struct.unpack(">BB", self.data[:2]), self.data[2:]


class OneByteProperty(AppParamProperty):
    length = 1  # byte
    fmt = ">B"

    def encode(self, data):
        return super(OneByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(OneByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class TwoByteProperty(AppParamProperty):
    length = 2  # bytes
    fmt = ">H"

    def encode(self, data):
        return super(TwoByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(TwoByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class EightByteProperty(AppParamProperty):
    length = 8  # bytes
    fmt = ">Q"

    def encode(self, data):
        return super(EightByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(EightByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class VariableLengthProperty(AppParamProperty):
    fmt = "{len}s"

    def encode(self, data):
        return super(VariableLengthProperty, self).encode(
            struct.pack(self.fmt.format(len=len(data)), data)
        )

    def decode(self):
        headers, data = super(VariableLengthProperty, self).decode()
        tagid, length = headers
        return struct.unpack(self.fmt.format(len=length), data)[0]


class PBAPType(UnicodeHeader):
    code = 0x42


class Order(OneByteProperty):
    tagid = 0x01


class SearchValue(VariableLengthProperty):
    tagid = 0x02


class SearchAttribute(OneByteProperty):
    tagid = 0x03


class MaxListCount(TwoByteProperty):
    tagid = 0x04


class ListStartOffset(TwoByteProperty):
    tagid = 0x05


class Filter(EightByteProperty):
    tagid = 0x06
    attr_dict = FILTER_ATTR_DICT


class Format(OneByteProperty):
    tagid = 0x07


class PhonebookSize(TwoByteProperty):
    tagid = 0x08


class NewMissedCalls(OneByteProperty):
    tagid = 0x09


app_parameters_dict = {
    0x01: Order,
    0x02: SearchValue,
    0x03: SearchAttribute,
    0x04: MaxListCount,
    0x05: ListStartOffset,
    0x06: Filter,
    0x07: Format,
    0x08: PhonebookSize,
    0x09: NewMissedCalls,
}


# Sample App Parameters data
# code | length | data
# 4c | 00 18 | 06 08 00 00 00 3f d0 00 00 80 07 01 00 04 02 00 00 05 02 00 00


def extended_decode(self):
    # assumption:
    # size of tagid = 1 byte
    # size of length = 1 byte (This is just the data length)
    data = self.data
    res_dict = {}
    while data:
        tagid = ord(data[0])
        length = ord(data[1])
        app_param_class = app_parameters_dict[tagid]
        res_dict[app_param_class.__name__] = app_param_class(
            data[: length + 2], encoded=True
        )
        data = data[length + 2 :]
    return res_dict


def extended_encode(self, data_dict):
    data = b""
    for item in data_dict.values():
        if item is None:
            continue
        data += item.data
    return struct.pack(">BH", self.code, len(data) + 3) + data


App_Parameters.decode = extended_decode
App_Parameters.encode = extended_encode
