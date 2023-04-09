# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Phone Book Access Profile client implemention"""


import atexit
import collections
import logging
import os
import readline
import sys

from xml.etree import ElementTree

import bluetooth
import cmd2
import pbapheaders as headers
import pbapresponses as responses

from optparse import make_option
from PyOBEX import client


logger = logging.getLogger(__name__)


class PBAPClient(client.Client):
    """PhoneBook Access Profile Client"""

    def __init__(self, address, port):
        client.Client.__init__(self, address, port)
        self.current_dir = "/"

    def pull_phonebook(
        self, name, filter_=0, format_=0, max_list_count=65535, list_startoffset=0
    ):
        """Retrieves entire phonebook object from current folder"""
        logger.info(
            "Requesting pull_phonebook for pbobject '%s' with appl parameters %s",
            name,
            str(locals()),
        )
        data = {
            "Filter": headers.Filter(filter_),
            "Format": headers.Format(format_),
            "MaxListCount": headers.MaxListCount(max_list_count),
            "ListStartOffset": headers.ListStartOffset(list_startoffset),
        }
        application_parameters = headers.App_Parameters(data, encoded=False)
        header_list = [headers.PBAPType("x-bt/phonebook")]
        if application_parameters.data:
            header_list.append(application_parameters)

        response = self.get(name, header_list)
        if not isinstance(response, tuple) and isinstance(
            response, responses.FailureResponse
        ):
            logger.error(
                "pull_phonebook failed for pbobject '%s'. reason = %s", name, response
            )
            return
        return response

    def pull_vcard_listing(
        self,
        name,
        order=0,
        search_value=None,
        search_attribute="N",
        max_list_count=65535,
        list_startoffset=0,
    ):
        """Retrieves phonebook listing object from current folder"""
        logger.info("Requesting pull_vcard_listing with parameters %s", str(locals()))
        data = {
            "Order": headers.Order(order),
            "MaxListCount": headers.MaxListCount(max_list_count),
            "ListStartOffset": headers.ListStartOffset(list_startoffset),
        }
        if search_value is not None and search_attribute is not None:
            data.update(
                {
                    "SearchValue": headers.SearchValue(search_value),
                    "SearchAttribute": headers.SearchAttribute(search_attribute),
                }
            )
        application_parameters = headers.App_Parameters(data, encoded=False)
        header_list = [headers.PBAPType("x-bt/vcard-listing")]
        if application_parameters.data:
            header_list.append(application_parameters)

        response = self.get(name, header_list)
        if not isinstance(response, tuple) and isinstance(
            response, responses.FailureResponse
        ):
            logger.error(
                "pull_vcard_listing failed for pbobject '%s'. reason = %s",
                name,
                response,
            )
            return
        return response

    def pull_vcard_entry(self, name, filter_=0, format_=0):
        """Retrieves specific vcard from pbap server"""
        logger.info(
            "Requesting pull_vcard_entry for pbobject with parameters %s", str(locals())
        )
        data = {"Filter": headers.Filter(filter_), "Format": headers.Format(format_)}

        application_parameters = headers.App_Parameters(data, encoded=False)
        header_list = [headers.PBAPType("x-bt/vcard")]
        if application_parameters.data:
            header_list.append(application_parameters)

        response = self.get(name, header_list)
        if not isinstance(response, tuple) and isinstance(
            response, responses.FailureResponse
        ):
            logger.error(
                "pull_vcard_entry failed for pbobject '%s'. reason = %s", name, response
            )
            return
        return response

    def set_phonebook(self, name="", to_root=False, to_parent=False):
        """Sets the current folder in the virtual folder architecture"""
        logger.info("Setting current folder with params '%s'", str(locals()))
        if name == "" and not to_parent and not to_root:
            logger.error(
                "Not a valid action, "
                "either name should be not empty or to_parent/to_root should be True"
            )
            return
        # TODO: not exactly as per spec, limited by pyobex setpath. need to refine further
        if to_root:
            path_comp = self.current_dir.split("/")[1:]
            if not any(path_comp):
                logger.warning("Path is already in root folder, no need to change")
                return
            for _ in path_comp:
                self.setpath(to_parent=True)
        elif to_parent:
            if self.current_dir == "/":
                logger.warning("Path is already in root folder, can't go to parent dir")
                return
            response = self.setpath(to_parent=True)
        else:
            response = self.setpath(name)

        if not isinstance(response, tuple) and isinstance(
            response, responses.FailureResponse
        ):
            logger.error("set_phonebook failed. reason = %s", name, response)
            return

        if to_root:
            self.current_dir = "/"
        elif to_parent:
            self.current_dir = os.path.dirname(self.current_dir)
        else:
            self.current_dir = os.path.join(self.current_dir, name)
        return response


class REPL(cmd2.Cmd):
    """REPL to use PBAP client"""

    def __init__(self):
        cmd2.Cmd.__init__(self)
        # self.prompt = self.colorize("pbap> ", "yellow")
        self.prompt = cmd2.ansi.style("pbap> ", fg=cmd2.ansi.Fg.YELLOW)
        # self.intro = self.colorize("Welcome to the PhoneBook Access Profile!", "green")
        self.intro = cmd2.ansi.style(
            "Welcome to the PhoneBook Access Profile!", fg=cmd2.ansi.Fg.GREEN
        )
        self.client = None
        self._store_history()
        # cmd2.set_use_arg_list(False)

    @staticmethod
    def _store_history():
        history_file = os.path.expanduser("~/.pbapclient_history")
        if not os.path.exists(history_file):
            with open(history_file, "w", encoding="latin1") as fobj:
                fobj.write("")
        readline.read_history_file(history_file)
        atexit.register(readline.write_history_file, history_file)

    # @cmd2.options([], arg_desc="server_address")
    def do_connect(self, line, opts):
        self.add_settable(cmd2.Settable(name="server_address", val_type=str))

        profile_id = "1130"  # profile id of PBAP
        service_id = b"\x79\x61\x35\xf0\xf0\xc5\x11\xd8\x09\x66\x08\x00\x20\x0c\x9a\x66"
        server_address = line
        if not server_address:
            raise ValueError("server_address should not be empty")
        logger.info("Finding PBAP service ...")
        services = bluetooth.find_service(address=server_address, uuid=profile_id)
        if not services:
            sys.stderr.write("No PBAP service found\n")
            sys.exit(1)

        host = services[0]["host"]
        port = services[0]["port"]
        logger.info("PBAP service found!")

        self.client = PBAPClient(host, port)
        logger.info("Connecting to pbap server = (%s, %s)", host, port)
        result = self.client.connect(header_list=[headers.Target(service_id)])
        if not isinstance(result, responses.ConnectSuccess):
            logger.error("Connect Failed, Terminating the Pbap client..")
            sys.exit(2)
        logger.info("Connect success")
        # self.prompt = self.colorize("pbap> ", "green")
        self.prompt = cmd2.ansi.style("pbap> ", fg=cmd2.ansi.Fg.GREEN)

    # @cmd2.options([], arg_desc="")
    def do_disconnect(self, line, opts):
        if self.client is None:
            logger.error(
                "PBAPClient is not even connected.. Connect and then try disconnect"
            )
            sys.exit(2)
        logger.debug("Disconnecting pbap client with pbap server")
        self.client.disconnect()
        self.client = None
        # self.prompt = self.colorize("pbap> ", "yellow")
        self.prompt = cmd2.ansi.style("pbap> ", fg=cmd2.ansi.Fg.YELLOW)

    # @cmd2.options(
    #     [
    #         make_option(
    #             "-f",
    #             "--filter",
    #             default=0x00000000,
    #             type=int,
    #             help="Attributes filter mask",
    #         ),
    #         make_option("-t", "--format", default=0, type=int, help="vcard format"),
    #         make_option(
    #             "-c",
    #             "--max-count",
    #             default=65535,
    #             type=int,
    #             help="maximum number of contacts to be returned",
    #         ),
    #         make_option(
    #             "-o",
    #             "--start-offset",
    #             default=0,
    #             type=int,
    #             help="offset of first entry to be returned",
    #         ),
    #     ],
    #     arg_desc="phonebook_name",
    # )
    def do_pull_phonebook(self, line, opts):
        """Returns phonebook as per requested options"""
        result = self.client.pull_phonebook(
            name=line,
            filter_=opts.filter,
            format_=opts.format,
            max_list_count=opts.max_count,
            list_startoffset=opts.start_offset,
        )
        if result is not None:
            _, data = result
            logger.info("Result of pull_phonebook:\n%s", data)

    pull_vcard_listing_parser = cmd2.Cmd2ArgumentParser()
    pull_vcard_listing_parser.add_argument(
        "-r",
        "--order",
        default=0,
        type=int,
        help="Ordering { Alphabetical | Indexed | Phonetical}",
    )
    pull_vcard_listing_parser.add_argument(
        "--search-attribute",
        default=0,
        type=int,
        help="SearchAttribute {Name | Number | Sound }",
    )
    pull_vcard_listing_parser.add_argument(
        "-c",
        "--max-count",
        default=65535,
        type=int,
        help="Maximum number of contacts to be returned",
    )
    pull_vcard_listing_parser.add_argument(
        "-o",
        "--start-offset",
        default=0,
        type=int,
        help="offset of first entry to be returned",
    )

    @cmd2.with_argparser(pull_vcard_listing_parser)
    def do_pull_vcard_listing(self, line, opts):
        """Returns vcardlisting as per requested options"""
        result = self.client.pull_vcard_listing(
            name=line,
            order=opts.order,
            search_value=opts.search_value,
            search_attribute=opts.search_attribute,
            max_list_count=opts.max_count,
            list_startoffset=opts.start_offset,
        )
        if result is not None:
            _, data = result
            logger.info("Result of pull_vcard_listing:\n%s", data)

    pull_vcard_entry_parser = cmd2.Cmd2ArgumentParser()
    pull_vcard_entry_parser.add_argument(
        "-f",
        "--filter",
        default=0x00000000,
        type=int,
        help="Attributes filter mask",
    )
    pull_vcard_entry_parser.add_argument(
        "-t",
        "--format",
        default=0,
        type=int,
        help="vcard format",
    )

    @cmd2.with_argparser(pull_vcard_entry_parser)
    def do_pull_vcard_entry(self, line, opts):
        """Returns a single vcardentry as per requested options"""
        result = self.client.pull_vcard_entry(
            name=line, filter_=opts.filter, format_=opts.format
        )
        if result is not None:
            header, data = result
            logger.info("Result of pull_vcard_entry:\n%s", data)

    # @cmd2.options(
    #     [
    #         make_option(
    #             "--to-parent",
    #             action="store_true",
    #             default=False,
    #             help="navigate to parent dir",
    #         ),
    #         make_option(
    #             "--to-root",
    #             action="store_true",
    #             default=False,
    #             help="navigate to root dir",
    #         ),
    #     ],
    #     arg_desc="[folder_name]",
    # )
    def do_set_phonebook(self, line, opts):
        """Set current folder path of pbapserver virtual folder"""
        result = self.client.set_phonebook(
            name=line, to_parent=opts.to_parent, to_root=opts.to_root
        )
        if result is not None:
            logger.info("Result of set_phonebook:\n%s", result)

    # @cmd2.options([], arg_desc="server_address [folder_name]")
    def do_mirror_vfolder(self, line, opts):
        """Downloads phonebook from pbapserver and save it in virtual folder architecture in FS"""
        args = line.split()
        self.do_connect(args[0] if len(args) else "")
        rootdir = args[1] if len(args) >= 2 else "phonebook_vfolder"
        # TODO: need to handle multiple SIM contacts
        os.makedirs(rootdir)
        for memory in ["sim_memory", "phone_memory"]:
            prefix = "" if memory == "phone_memory" else "SIM1/"
            telecom_dir = os.path.join(rootdir, prefix, "telecom")
            os.makedirs(telecom_dir)
            phobject_filename_map = collections.defaultdict(list)
            phonebook_objects = ["spd", "fav", "pb", "ich", "och", "mch", "cch"]
            for pbobject in phonebook_objects:
                current_dir = os.path.join(telecom_dir, pbobject)
                os.makedirs(current_dir)
                # Access the list of vcards in the phone's internal phone book.
                response = self.client.pull_vcard_listing(
                    "{prefix}telecom/{pbobject}".format(
                        prefix=prefix, pbobject=pbobject
                    )
                )
                if response is None:
                    logger.error(
                        "vcard-listing get is failed for pbobject '%s'", pbobject
                    )
                    continue
                hdrs, cards = response
                # Parse the XML response to the previous request.
                root = ElementTree.fromstring(cards)
                logger.info("\nAvailable cards in %stelecom/%s\n", prefix, pbobject)
                names = []
                # Examine each XML element, storing the file names we find in a list, and
                # printing out the file names and their corresponding contact names.
                for card in root.findall("card"):
                    logger.info("%s: %s", card.attrib["handle"], card.attrib["name"])
                    names.append(card.attrib["handle"])
                phobject_filename_map[pbobject] = names

                logger.info("\nCards in %stelecom/%s\n", prefix, pbobject)
                # Request all the file names obtained earlier.
                self.client.set_phonebook(
                    "{prefix}telecom/{pbobject}".format(
                        prefix=prefix, pbobject=pbobject
                    )
                )
                for name in names:
                    response = self.client.pull_vcard_entry(name)
                    if response is None:
                        logger.error("vcard get is failed for pbobject '%s'", response)
                        continue
                    hdrs, card = response
                    logger.info(card)
                    with open(os.path.join(current_dir, name), "w+") as f:
                        f.write(card)

                logger.debug("current_dir = %s", current_dir)
                # Return to the root directory.
                self.client.set_phonebook(to_parent=True)
                current_dir = os.path.normpath(os.path.join(current_dir, ".."))
                logger.debug("current_dir = %s", current_dir)
                self.client.set_phonebook(to_parent=True)
                current_dir = os.path.normpath(os.path.join(current_dir, ".."))
                if prefix:
                    self.client.set_phonebook(to_parent=True)
                    current_dir = os.path.normpath(os.path.join(current_dir, ".."))

                logger.debug("current_dir = %s", current_dir)
                logger.info(
                    "\nThe phonebook in %s/telecom/%s as one vcard\n", prefix, pbobject
                )
                response = self.client.pull_phonebook(
                    "{prefix}telecom/{pbobject}.vcf".format(
                        prefix=prefix, pbobject=pbobject
                    )
                )
                if response is None:
                    logger.error("phonebook get is failed for pbobject '%s'", pbobject)
                    continue
                hdrs, phonebook = response
                logger.info(phonebook)
                with open(
                    os.path.join(current_dir, prefix, "telecom", pbobject + ".vcf"),
                    "w+",
                ) as f:
                    f.write(phonebook)
                logger.info(hdrs)

        self.do_disconnect("")

    do_q = cmd2.Cmd.do_quit


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)-8s %(message)s"
    )
    repl = REPL()
    repl.cmdloop()
