# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Phone Book Access Profile server implementation"""

import argparse
import logging
import os
import sys

# from bluetooth import OBEX_UUID, RFCOMM_UUID, L2CAP_UUID,
from bluetooth import PORT_ANY
from PyOBEX import requests, server

import pbapheaders as headers
import pbapresponses as responses

from pbapcommon import FILTER_ATTR_DICT, MANDATORY_ATTR_BITMASK
from vfolder import VFolderPhoneBook_FS, VFolderPhoneBook_DB
from vcard_helper import VCard

logger = logging.getLogger(__name__)


class PbapServer(server.Server):

    def __init__(self, address, rootdir="/", use_fs=True):
        server.Server.__init__(self, address)
        self.vfolder = VFolderPhoneBook_FS(rootdir) if use_fs else VFolderPhoneBook_DB(rootdir)

    def process_request(self, connection, request):
        """Processes the request from the connection."""
        if isinstance(request, requests.Connect):
            logger.debug("Request type = connect")
            self.connect(connection, request)
        elif isinstance(request, requests.Disconnect):
            logger.debug("Request type = disconnect")
            self.disconnect(connection, request)
        elif isinstance(request, requests.Put):
            logger.debug("Request type = put")
            self.put(connection, request)
        elif isinstance(request, requests.Get):
            logger.debug("Request type = get")
            self.get(connection, request)
        elif isinstance(request, requests.Set_Path):
            logger.debug("Request type = setpath")
            self.setpath(connection, request)
        else:
            logger.debug("Request type = Unknown. so rejected")
            self._reject(connection)

    def disconnect(self, socket, request):
        server.Server.disconnect(self, socket, request)
        self.vfolder.curdir = self.vfolder.rootdir

    def setpath(self, socket, request):
        decoded_header = self._decode_header_data(request)
        createdir = not bool(request.flags & request.DontCreateDir)
        toparent = bool(request.flags & request.NavigateToParent)
        logger.info("createdir = %r" % createdir)
        logger.info("toparent = %r" % toparent)
        # TODO: set_phonebook, to_root is not yet supported
        # This is just a overloaded version of obex setpath
        if toparent:
            if self.vfolder.curdir == self.vfolder.rootdir:
                logger.error("Current directory is same as Root dir, so can't go to parent")
                self.send_response(socket, responses.Forbidden())
                return
            else:
                self.vfolder.curdir = self.vfolder.join(self.vfolder.curdir, "..")
                logger.info("Setting current directory = %s", self.vfolder.curdir)
                if decoded_header["Name"] == "":
                    logger.debug("Sending response success")
                    self.send_response(socket, responses.Success())
                    return

        requested_dir = self.vfolder.join(self.vfolder.curdir, decoded_header["Name"])
        if createdir:
            if self.vfolder.isdir(requested_dir):
                logger.error("Requested path already exists, so can't create it again.")
                self.send_response(socket, responses.Precondition_Failed())
                return
            else:
                logger.info("Creating new directory = %s", requested_dir)
                self.vfolder.makedirs(requested_dir)
                self.vfolder.curdir = requested_dir
                logger.info("Setting current directory = %s", self.vfolder.curdir)
                logger.debug("Sending response success")
                self.send_response(socket, responses.Success())
                return

        if not self.vfolder.isdir(requested_dir):
            logger.error("Requested path not exists, so can't set it to current dir")
            self.send_response(socket, responses.Precondition_Failed())
            return
        else:
            self.vfolder.curdir = requested_dir
            logger.info("Setting current directory = %s", self.vfolder.curdir)
            logger.debug("Sending response success")
            self.send_response(socket, responses.Success())
            return

    def get(self, socket, request):
        decoded_header = self._decode_header_data(request)
        if request.is_final():
            logger.debug("request is final")
            if decoded_header["Type"] == "x-bt/vcard-listing":
                self._pull_vcard_listing(socket, request, decoded_header)
            elif decoded_header["Type"] == "x-bt/vcard":
                self._pull_vcard_entry(socket, request, decoded_header)
            elif decoded_header["Type"] == "x-bt/phonebook":
                self._pull_phonebook(socket, request, decoded_header)
            else:
                logger.error("Requested type = %s is not supported yet.", decoded_header["Type"])
                self.send_response(socket, responses.Bad_Request())

    def _pull_vcard_listing(self, socket, request, decoded_header):
        mch_size = 0  # mch_size for phonebook folder (Don't optimize)
        abs_name = self.vfolder.join(self.vfolder.curdir, decoded_header["Name"])
        logger.info("Absolute path of requested vcard_listing object = %s", abs_name)
        app_params = self._decode_app_params(decoded_header.get("App_Parameters", {}))
        if not self.vfolder.isdir(abs_name):
            logger.error("Requested vcard-listing dir doesn't exists")
            self.send_response(socket, responses.Not_Found())
        else:
            phonebook_size = self.vfolder.count(abs_name)
            search_query = self._get_search_query(app_params["SearchAttribute"], app_params["SearchValue"])
            # TODO: sorting based on order not works, since handle is not part of db record. it is not proper
            # make the "handle" as part of db record
            sort_key = self._get_sort_key(app_params["Order"])
            vcard_list = self.vfolder.listdir(abs_name, query=search_query)
            vcard_list = self._sort_vcard_list(vcard_list, sort_key)

            if app_params["MaxListCount"] == 0:
                self._respond_phonebook_size(socket, phonebook_size)
                return

            data = ""
            res_vcard_list = self._limit_phonebook(vcard_list, app_params["MaxListCount"],
                                                   app_params["ListStartOffset"])
            res_vcard_list_range = range(app_params["ListStartOffset"],
                                         min((app_params["ListStartOffset"] + app_params["MaxListCount"]), 65535))
            # "NewMissedCalls": This application parameter shall be used in the response when and only when the
            # phone book object is mch. It indicates the number of missed calls that have been
            # received on the PSE since the last PullPhoneBook request on the mch folder, at the
            # point of the request.
            if "mch" in abs_name:
                response_dict = {'NewMissedCalls': headers.NewMissedCalls(phonebook_size - mch_size)}
                mch_size = phonebook_size
            else:
                response_dict = {}

            vcard_listing_object_tmpl = ('<?xml version="1.0"?>\r\n'
                                         '<!DOCTYPE vcard-listing SYSTEM "vcard-listing.dtd">\r\n'
                                         '<vCard-listing version="1.0">\r\n'
                                         '{cards}'
                                         '</vCard-listing>\r\n')
            card_tag_tmpl = '<card handle="{handle}" name="{name}"/>\r\n'
            cards = ""
            # TODO: As per spec the handles should be hex??
            for index, vcard in zip(res_vcard_list_range, res_vcard_list):
                cards += card_tag_tmpl.format(handle="{}.vcf".format(index),
                                              name=self._get_param_values(vcard, "N"))
            data = vcard_listing_object_tmpl.format(cards=cards)
            logger.debug("Sending response success with following data")
            logger.debug("vcard-listing data: \r\n%s", data)
            self.send_response(socket, responses.Success(),
                               [headers.End_Of_Body(data), headers.App_Parameters(response_dict)])

    def _get_param_values(self, vcard, param_name):
        for param in vcard["vcard"]:
            if param["type"] == param_name:
                return ";".join(param["values"])

    def _pull_vcard_entry(self, socket, request, decoded_header):
        abs_name = self.vfolder.join(self.vfolder.curdir, decoded_header["Name"])
        logger.info("Absolute path of requested vcard_entry object = %s", abs_name)
        app_params = self._decode_app_params(decoded_header.get("App_Parameters", {}))
        if not self.vfolder.isfile(abs_name):
            logger.error("Requested vcard file doesn't exists")
            self.send_response(socket, responses.Not_Found())
        else:
            filtered_data = self._filter_attributes(app_params["Filter"],
                                                    self.vfolder.read(abs_name),
                                                    app_params["Format"])
            data = VCard(filtered_data, parsed=True).serialize(app_params["Format"])
            logger.debug("Sending response success with following data")
            logger.debug("vcard data: \r\n%s", data)
            self.send_response(socket, responses.Success(), [
                               headers.End_Of_Body(data)])

    def _pull_phonebook(self, socket, request, decoded_header):
        mch_size = 0  # mch_size for phonebook folder (Don't optimize)
        abs_name = self.vfolder.join(self.vfolder.curdir, decoded_header["Name"])
        logger.info("Absolute path of requested phonebook object = %s", abs_name)
        app_params = self._decode_app_params(decoded_header.get("App_Parameters", {}))
        if not self.vfolder.isfile(abs_name):
            logger.error("Requested phonebook file doesn't exists")
            self.send_response(socket, responses.Not_Found())
        else:
            phonebook_size = self.vfolder.count(os.path.splitext(abs_name)[0])
            vcard_list = self.vfolder.listdir(os.path.splitext(abs_name)[0])

            if app_params["MaxListCount"] == 0:
                self._respond_phonebook_size(socket, phonebook_size)
                return

            data = ""
            res_vcard_list = self._limit_phonebook(vcard_list, app_params["MaxListCount"],
                                                   app_params["ListStartOffset"])
            # "NewMissedCalls": This application parameter shall be used in the response when and only when the
            # phone book object is mch. It indicates the number of missed calls that have been
            # received on the PSE since the last PullPhoneBook request on the mch folder, at the
            # point of the request.
            if "mch" in abs_name:
                response_dict = {'NewMissedCalls': headers.NewMissedCalls(phonebook_size - mch_size)}
                mch_size = phonebook_size
            else:
                response_dict = {}

            for item in res_vcard_list:
                filtered_data = self._filter_attributes(app_params["Filter"], item, app_params["Format"])
                data += VCard(filtered_data, parsed=True).serialize(app_params["Format"])

            logger.debug("Sending response success with following data")
            logger.debug("phonebook data: \r\n%s", data)

            # Sends the chunked response
            # TODO: This needs to be handled properly in pyobex: server.py: send_response
            bytes_transferred = 0
            datasize = len(data)
            # ideally max data length per packet should be as follows
            # max_datalen = self._max_length() - Message().minimum_length
            # but because of some unknown reasons we could only able to transmit ~700 bytes
            # TODO: figure out exactly what is the reason
            max_datalen = 700
            if datasize < max_datalen:
                data_last_chunk = data
            else:
                while bytes_transferred < datasize:
                    data_chunk = data[bytes_transferred: (bytes_transferred + max_datalen)]
                    header_list = [headers.App_Parameters(response_dict), headers.Body(data_chunk)]
                    # 'continue' response and process the subsequent requests
                    self.send_response(socket, responses.Continue(), header_list)
                    while True:
                        request = self.request_handler.decode(self.connection)
                        if not isinstance(request, requests.Get_Final):
                            self.process_request(self.connection, request)
                            continue
                        else:
                            break
                    bytes_transferred += max_datalen
                data_last_chunk = ""

            header_list = [headers.App_Parameters(response_dict), headers.End_Of_Body(data_last_chunk)]
            self.send_response(socket, responses.Success(), header_list)

    def _get_search_query(self, searchattribute, searchvalue):
        if searchattribute == 0x00:
            searchattribute = "N"
        elif searchattribute == 0x01:
            searchattribute = "Number"
        elif searchattribute == 0x02:
            searchattribute = "Sound"
        else:
            logger.error("Unsupported value for SearchAttribute=%s", searchattribute)
            return {}
        query = {"vcard": {"$elemMatch": {'type': searchattribute, 'values': {"$in": [searchvalue]}}}}
        return query if searchvalue else {}

    def _get_sort_key(self, order):
        if order == 0:  # Indexed order
            sort_key = ("_id", 1)
        elif order == 1:  # Alphanumeric order
            sort_key = ("N", 1)
        else:  # Phonetical order
            sort_key = ("SOUND", 1)
        return sort_key

    def _sort_vcard_list(self, vcard_list, sort_key):
        def _key_func(item):
            for param in item["vcard"]:
                if param["type"] == sort_key[0]:
                    return ";".join(param["values"])
        return sorted(vcard_list, key=_key_func)

    def _respond_phonebook_size(self, socket, phonebook_size):
        # MaxListCount = 0 signifies to the PSE that the PCE wants to know the number of used
        # indexes in the phone book of interest.
        # When MaxListCount = 0, the PSE shall ignore all other application parameters that may
        # be present in the request. The response shall include the PhonebookSize application
        # parameter (see Section 5.1.4.5). The response shall not contain any Body header
        logger.debug("MaxListCount is 0, so responding with PhonebookSize = {}".format(
            phonebook_size))
        response_dict = {'PhonebookSize': headers.PhonebookSize(phonebook_size)}
        self.send_response(socket, responses.Success(), [
                           headers.App_Parameters(response_dict)])

    def _decode_header_data(self, request):
        """Decodes all headers in given request and return the decoded values in dict"""
        header_dict = {}
        for header in request.header_data:
            if isinstance(header, headers.Name):
                header_dict["Name"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Name = %s" % header_dict["Name"])
            elif isinstance(header, headers.Length):
                header_dict["Length"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Length = %i" % header_dict["Length"])
            elif isinstance(header, headers.Type):
                header_dict["Type"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Type = %s" % header_dict["Type"])
            elif isinstance(header, headers.Connection_ID):
                header_dict["Connection_ID"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Connection ID = %s" % header_dict["Connection_ID"])
            elif isinstance(header, headers.App_Parameters):
                header_dict["App_Parameters"] = header.decode()
                logger.info("App Parameters are :")
                for param, value in header_dict["App_Parameters"].items():
                    logger.info("{param}: {value}".format(param=param, value=value.decode()))
            else:
                logger.error("Some Header data is not yet added in _decode_header_data")
                raise NotImplementedError("Some Header data is not yet added in _decode_header_data")
        return header_dict

    def _limit_phonebook(self, vcard_list, max_listcount, list_startoffset=0):
        """limit the phonebook size based on max listcount and list startoffset
        and update the index of phonebook accordingly."""
        vcard_list = vcard_list[list_startoffset:]
        if max_listcount != 65535:  # Range: 0 <= max_listcount <= 65535 (65535 => Unrestricted)
            vcard_list = vcard_list[:max_listcount]
        return vcard_list

    def _decode_app_params(self, app_params):
        """This will decode or populate app_params with default value."""
        decoded_app_params = {}
        if "Order" in app_params:
            decoded_app_params["Order"] = app_params["Order"].decode()
        else:
            decoded_app_params["Order"] = 0x00  # Default: Indexed Ordering
        if "SearchValue" in app_params:
            decoded_app_params["SearchValue"] = app_params["SearchValue"].decode()
        else:
            decoded_app_params["SearchValue"] = ""
        if "SearchAttribute" in app_params:
            decoded_app_params["SearchAttribute"] = app_params["SearchAttribute"].decode()
        else:
            decoded_app_params["SearchAttribute"] = 0  # Default: Name attribute
        if "MaxListCount" in app_params:
            decoded_app_params["MaxListCount"] = app_params["MaxListCount"].decode()
        else:
            decoded_app_params["MaxListCount"] = 65535
        if "ListStartOffset" in app_params:
            decoded_app_params["ListStartOffset"] = app_params["ListStartOffset"].decode()
        else:
            decoded_app_params["ListStartOffset"] = 0  # Default: 0
        if "Filter" in app_params:
            decoded_app_params["Filter"] = app_params["Filter"].decode()
        else:
            decoded_app_params["Filter"] = 0  # Default: 0 [means should return all the attributes]
        if "Format" in app_params:
            decoded_app_params["Format"] = "3.0" if app_params["Format"].decode() else "2.1"
        else:
            decoded_app_params["Format"] = "2.1"  # Default: v2.1
        if "PhonebookSize" in app_params:
            decoded_app_params["PhonebookSize"] = app_params["PhonebookSize"].decode()
        if "NewMissedCalls" in app_params:
            decoded_app_params["NewMissedCalls"] = app_params["NewMissedCalls"].decode()
        return decoded_app_params

    def _filter_attributes(self, filter_bitmask, data, vcard_version="2.1"):
        """receives filter bitmask and vcard data as dict then returns the filtered dict"""
        logger.debug("Filtering attributes for bitmask: {bitmask} data: {data}".format(
            bitmask=filter_bitmask, data=data))
        # if filter is 0, return all the attributes
        if filter_bitmask == 0:
            return data
        unfiltered_attrs = set()
        logger.debug("Adding mandatory attributes to necessary attributes list")
        filter_bitmask |= MANDATORY_ATTR_BITMASK[vcard_version]
        for bitmarker, attr_tuple in FILTER_ATTR_DICT.items():
            bit = 1 << bitmarker
            if bit & filter_bitmask == bit:
                unfiltered_attrs.add(attr_tuple[0])
        logger.debug("Necessary attributes: {unfiltered}".format(unfiltered=unfiltered_attrs))
        for param in data["vcard"][:]:
            attr = param["type"]
            if attr in unfiltered_attrs:
                continue
            else:
                data["vcard"].remove(param)
        return data

    def serve(self, socket):
        """Override: changes 'connection' as instance variable.
        So we can access it in other methods, enables handling
        of 'Continue' response and subsequent requests
        """
        while True:
            self.connection, self.address = socket.accept()
            if not self.accept_connection(*self.address):
                self.connection.close()
                continue
            logger.info("PBAP, Connection from %s", self.address)
            self.connected = True
            while self.connected:
                request = self.request_handler.decode(self.connection)
                self.process_request(self.connection, request)

    def start_service(self, port=PORT_ANY):

        # Service Name: OBEX Phonebook Access Server
        # Service RecHandle: 0x1000b
        # Service Class ID List:
        #   "Phonebook Access - PSE" (0x112f)
        # Protocol Descriptor List:
        #   "L2CAP" (0x0100)
        #   "RFCOMM" (0x0003)
        #     Channel: 19
        #   "OBEX" (0x0008)
        # Profile Descriptor List:
        #   "Phonebook Access" (0x1130)
        #     Version: 0x0101

        name = "OBEX Phonebook Access Server"
        uuid = "796135F0-F0C5-11D8-0966-0800200C9A66"
        service_classes = ["112f"]
        service_profiles = [("1130", 0x0101)]
        provider = "BMW CarIT GmbH"
        description = "Phonebook Access Profile - PSE"
        # Adding protocols to service discovery crashes the process
        # protocols = [L2CAP_UUID, RFCOMM_UUID, OBEX_UUID]

        return server.Server.start_service(
            self, port, name, uuid, service_classes, service_profiles,
            provider, description, []
        )


def run_server(device_address, rootdir, use_fs):
    # Run the server in a function so that, if the server causes an exception
    # to be raised, the server instance will be deleted properly, giving us a
    # chance to create a new one and start the service again without getting
    # errors about the address still being in use.
    pbap_server = PbapServer(device_address, rootdir, use_fs)
    socket = pbap_server.start_service(port=PORT_ANY)
    try:
        pbap_server.serve(socket)
    except KeyboardInterrupt:
        logger.info("Exiting the pbapserver...")
        exit(0)
    finally:
        pbap_server.stop_service(socket)


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(levelname)-8s %(message)s')

    parser = argparse.ArgumentParser(description="Phonebook Access Profile")
    parser.add_argument("--address", required=True,
                        help="bluetooth address to start the server")
    parser.add_argument("--use-fs", action="store_true",
                        help="Use the phonebook virtual folder stored in filesystem."
                             "(if not given will use the phonebook from mongodb)")
    parser.add_argument("--rootdir", help="rootdir of phonebook virtual folder, "
                                          "required while using filesystem as storage")
    args = parser.parse_args()

    if args.use_fs and args.rootdir is None:
        parser.error("rootdir is required if filesystem storage is specified")
    elif not args.use_fs:
        rootdir = "/"
    else:
        rootdir = args.rootdir

    while True:
        run_server(device_address=args.address, rootdir=rootdir, use_fs=args.use_fs)

    sys.exit(0)


if __name__ == "__main__":
    main()
