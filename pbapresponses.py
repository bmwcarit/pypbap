# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Extension to PyOBEX responses needed for PBAP"""


from PyOBEX.responses import *


class Not_Acceptable(FailureResponse):
    code = OBEX_Not_Acceptable = 0xC6


class Not_Implemented(FailureResponse):
    code = OBEX_Not_Implemented = 0xD1


class Service_Unavailable(FailureResponse):
    code = OBEX_Service_Unavailable = 0xD3


ResponseHandler.message_dict.update({
    Not_Acceptable.code: Not_Acceptable,
    Not_Implemented.code: Not_Implemented,
    Service_Unavailable.code: Service_Unavailable
})
