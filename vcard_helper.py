# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""VCard helper module is used to parse vcard strings to dict(version independent) and vice versa"""
# pylint: disable=invalid-name

import codecs
import copy
import logging

logger = logging.getLogger(__name__)


class VCard(object):
    """Constructs the vcard objects and parses the vcard string"""

    def __init__(self, vcard, parsed=False):
        self.vcf_dict = vcard if parsed else self.parse(vcard)

    def unfold(self, vcard):
        """Unfolds the folded lines of vcard"""
        unfolded_vcard = []
        vcard_properties = tuple(VCardProperties.keys())
        for line in vcard.splitlines():
            if line.startswith(vcard_properties) or line.startswith("X-"):
                unfolded_vcard.append(line)
            else:
                unfolded_vcard[-1] += line
        return unfolded_vcard

    def serialize(self, version="2.1"):
        """Serializes the current vcard object into string"""
        vcf_str = ""
        for vcard_prop_dict in self.denormalize(self.to_dict(), version)["vcard"]:
            vcard_property_class = VCardProperties[vcard_prop_dict["type"]]
            vcf_str += vcard_property_class(vcard_prop_dict, parsed=True).serialize(version)
        return vcf_str

    def normalize(self, vcf_dict):
        """converts version dependent vcard dict to version independent one"""
        # removes begin, version, end properties which will be added on denormalization
        vcf_dict_copy = copy.deepcopy(vcf_dict)
        vcf_dict_copy['vcard'].pop(0)
        vcf_dict_copy['vcard'].pop(0)
        vcf_dict_copy['vcard'].pop()
        return vcf_dict_copy

    def denormalize(self, vcf_dict, version="2.1"):
        """converts version independent vcard dict to version dependent one"""
        vcf_dict_copy = copy.deepcopy(vcf_dict)
        begin_dict = {'values': ['VCARD'], 'type': 'BEGIN', 'parameters': []}
        version_dict = {'values': ['{version}'.format(version=version)], 'type': 'VERSION', 'parameters': []}
        end_dict = {'values': ['VCARD'], 'type': 'END', 'parameters': []}
        vcf_dict_copy['vcard'].insert(0, begin_dict)
        vcf_dict_copy['vcard'].insert(1, version_dict)
        vcf_dict_copy['vcard'].append(end_dict)
        return vcf_dict_copy

    def to_dict(self):
        """Converts the current vcard object into python dict"""
        return self.vcf_dict

    def from_dict(self, vcf_dict, normalized=False):
        """Constructs the vcard object using the vcf_dict"""
        self.vcf_dict = vcf_dict if normalized else self.normalize(vcf_dict)

    def _get_property_type(self, prop):
        """Extracts the type of property from property string"""
        return prop.partition(":")[0].partition(";")[0]

    def _split_into_properties(self, vcf_str):
        """Splits vcf string into list of property objects"""
        prop_obj_list = []
        prop_list = self.unfold(vcf_str)
        for prop in prop_list:
            prop_type = self._get_property_type(prop)
            if prop_type not in VCardProperties:
                logger.error("=" * 80)
                logger.error("Unsupported Property type: %s", prop_type)
                logger.error("=" * 80)
            else:
                prop_obj_list.append(VCardProperties[prop_type.upper()](prop))
        return prop_obj_list

    def parse(self, vcf_str):
        """Parse the vcf_str and constructs the vcard objects using that"""
        if not vcf_str:
            raise TypeError("Given input vcard string shouldn't be empty")
        self.vcf_str = vcf_str
        self.vcard_properties = self._split_into_properties(self.vcf_str)
        vcf_dict = {"vcard": [prop.to_dict() for prop in self.vcard_properties]}
        return self.normalize(vcf_dict)


class VCardProperty(object):
    """Represents property of VCard"""
    STR_TEMPLATE = "{type}{sep}{param}:{value}\r\n"

    def __init__(self, vcard, parsed=False):
        self.vcf_dict = vcard if parsed else self.parse(vcard)

    def serialize(self, version="2.1"):
        """Serializes the current vcard property into string"""
        vcf_dict = self.denormalize(self.vcf_dict, version)
        params = self._tuples_to_params(vcf_dict["parameters"])
        vcf_result = self.STR_TEMPLATE.format(type=vcf_dict["type"],
                                              sep=";" if params else "",
                                              param=params,
                                              value=";".join([item.encode('utf-8') for item in vcf_dict["values"]]))
        return vcf_result

    def to_dict(self):
        """Converts the current vcard property into python dict"""
        return self.vcf_dict

    def from_dict(self, vcf_dict, normalized=False):
        """Constructs the vcard property using the vcf_dict"""
        self.vcf_dict = vcf_dict if normalized else self.normalize(vcf_dict)

    def normalize(self, vcf_dict):
        """converts version dependent vcard dict to version independent one"""
        return vcf_dict

    def denormalize(self, vcf_dict, version="2.1"):
        """converts version independent vcard dict to version dependent one"""
        return vcf_dict

    def _params_to_tuple(self, params):
        """splits the params into list of tuples"""
        param_list = []
        if not params:
            return param_list
        for param in params.split(";"):
            type_, _, value = param.rpartition("=")
            param_list.append((type_, value))
        return param_list

    def _tuples_to_params(self, param_tuples):
        """constructs the params string using the list of param tuples"""
        param_str = ""
        for param in param_tuples:
            key, value = param
            if not key:
                param_str += "{value};".format(value=value)
            else:
                param_str += "{key}={value};".format(key=key, value=value)
        return param_str.rstrip(";")

    def parse(self, vcf_str):
        """Parse the vcf_str and constructs the vcard property using that"""
        if not vcf_str:
            raise TypeError("Input vcard string is empty")
        self.vcf_str = vcf_str
        lhs, _, rhs = self.vcf_str.partition(":")
        type_, _, params = lhs.partition(";")
        vcf_dict = {
            "type": type_,
            "values": rhs.split(";"),
            "parameters": self._params_to_tuple(params)
        }
        return self.normalize(vcf_dict)


class VCardProperty_CharsetEncodingParamNormalized(VCardProperty):
    """Overloaded VCardProperty which normalizes charset and encoding Params"""

    def normalize(self, vcf_dict):
        """converts version dependent vcard dict to version independent one"""
        vcf_dict = super(VCardProperty_CharsetEncodingParamNormalized, self).normalize(vcf_dict)
        vcf_dict = copy.deepcopy(vcf_dict)
        charset = None
        encoding = None
        for param in vcf_dict["parameters"][:]:
            if param[0].upper() == "ENCODING":
                encoding = param[1]
                vcf_dict["parameters"].remove(param)
            elif param[0].upper() == "CHARSET":
                charset = param[1]
                vcf_dict["parameters"].remove(param)
            elif param[0].upper() == "" or param[0].upper() == "TYPE":
                vcf_dict["parameters"].remove(param)
                vcf_dict["parameters"].append(("TYPE", param[1]))
        if encoding:
            value, _ = codecs.lookup(encoding).decode(";".join(vcf_dict["values"]))
            vcf_dict["values"] = value.split(";")
        if charset:
            value, _ = codecs.lookup(charset).decode(";".join(vcf_dict["values"]), errors="replace")
            vcf_dict["values"] = value.split(";")
        vcf_dict["values"] = ";".join(vcf_dict["values"]).encode("utf8").split(";")
        return vcf_dict

    def denormalize(self, vcf_dict, version="2.1"):
        """converts version independent vcard dict to version dependent one"""
        vcf_dict = super(VCardProperty_CharsetEncodingParamNormalized, self).denormalize(vcf_dict, version)
        vcf_dict = copy.deepcopy(vcf_dict)
        encoding = "QUOTED-PRINTABLE"
        charset = "UTF-8"
        if version == "2.1":
            # value is already in "UTF-8" charset so no need to re-encode
            value, _ = codecs.lookup(encoding).encode(";".join(vcf_dict["values"]))
            vcf_dict["values"] = value.split(";")
            for param in vcf_dict["parameters"][:]:
                if param[0].upper() == "TYPE":
                    vcf_dict["parameters"].remove(param)
                    vcf_dict["parameters"].append(("", param[1]))
            vcf_dict["parameters"].append(("CHARSET", charset))
            vcf_dict["parameters"].append(("ENCODING", encoding))
        return vcf_dict


class VCardProperty_BASE64EncodingParamNormalized(VCardProperty):
    """Overloaded VCardProperty with Type and Encoding Params Normalized"""

    def normalize(self, vcf_dict):
        """converts version dependent vcard dict to version independent one"""
        vcf_dict = super(VCardProperty_BASE64EncodingParamNormalized, self).normalize(vcf_dict)
        vcf_dict = copy.deepcopy(vcf_dict)
        normalized_params = []
        for param in vcf_dict["parameters"]:
            if param[0].upper() == "ENCODING":
                normalized_params.append(("ENCODING", "b"))  # key property only have base64 encoding
            elif param[0].upper() == "" or param[0].upper() == "TYPE":
                normalized_params.append(("TYPE", param[1]))
            else:
                normalized_params.append(param)
        vcf_dict["parameters"] = normalized_params
        return vcf_dict

    def denormalize(self, vcf_dict, version="2.1"):
        """converts version independent vcard dict to version dependent one"""
        vcf_dict = super(VCardProperty_BASE64EncodingParamNormalized, self).denormalize(vcf_dict, version)
        vcf_dict = copy.deepcopy(vcf_dict)
        denormalized_params = []
        for param in vcf_dict["parameters"]:
            if param[0].upper() == "ENCODING":
                if version == "2.1":
                    denormalized_params.append(("ENCODING", "BASE64"))  # key property only have base64 encoding
                elif version == "3.0":
                    denormalized_params.append(("ENCODING", "b"))  # key property only have base64 encoding
                else:
                    raise TypeError("Unsupported version")
            elif param[0].upper() == "TYPE":
                if version == "2.1":
                    denormalized_params.append(("", param[1]))
                elif version == "3.0":
                    denormalized_params.append(("TYPE", param[1]))
                else:
                    raise TypeError("Unsupported version")
            else:
                denormalized_params.append(param)
        vcf_dict["parameters"] = denormalized_params
        return vcf_dict


class Adr(VCardProperty_CharsetEncodingParamNormalized):
    """A structured representation of the physical delivery address for the vCard object."""


class Agent(VCardProperty):
    """Information about another person who will act on behalf of the vCard object.
    Typically this would be an area administrator, assistant, or secretary for the individual.
    Can be either a URL or an embedded vCard.
    """


class Begin(VCardProperty):
    """All vCards must start with this property."""


class End(VCardProperty):
    """All vCards must end with this property."""


class Version(VCardProperty):
    """The version of the vCard specification.
    In versions 3.0 and 4.0, this must come right after the BEGIN property.
    """


class N(VCardProperty_CharsetEncodingParamNormalized):
    """A structured representation of the name of the person,
    place or thing associated with the vCard object."""


class FN(VCardProperty_CharsetEncodingParamNormalized):
    """The formatted name string associated with the vCard object."""


class Birthday(VCardProperty):
    """Date of birth of the individual associated with the vCard."""


class Categories(VCardProperty):
    """A list of "tags" that can be used to describe the object represented by this vCard."""


class Class(VCardProperty):
    """Describes the sensitivity of the information in the vCard."""


class Email(VCardProperty_CharsetEncodingParamNormalized):
    """The address for electronic mail communication with the vCard object."""


class GEO(VCardProperty):
    """Specifies a latitude and longitude."""


class IMPP(VCardProperty_CharsetEncodingParamNormalized):
    """Defines an instant messenger handle."""


class Key(VCardProperty_BASE64EncodingParamNormalized):
    """The public encryption key associated with the vCard object.
    It may point to an external URL, may be plain text, or
    may be embedded in the vCard as a Base64 encoded block of text.
    """


class Label(VCardProperty_CharsetEncodingParamNormalized):
    """Represents the actual text that should be put on the mailing label when delivering a
    physical package to the person/object associated with the vCard (related to the ADR property)
    """


class Logo(VCardProperty_BASE64EncodingParamNormalized):
    """An image or graphic of the logo of the organization that is associated with the individual
    to which the vCard belongs. It may point to an external URL or
    may be embedded in the vCard as a Base64 encoded block of text.
    """


class Mailer(VCardProperty_CharsetEncodingParamNormalized):
    """Type of email program used."""


class Name(VCardProperty):
    """Provides a textual representation of the SOURCE property."""


class Nickname(VCardProperty):
    """One or more descriptive/familiar names for the object represented by this vCard."""


class Note(VCardProperty):
    """Specifies supplemental information or a comment that is associated with the vCard."""


class Org(VCardProperty_CharsetEncodingParamNormalized):
    """The name and optionally the unit(s) of the organization associated with the vCard object.
    This property is based on the X.520 Organization Name attribute and
    the X.520 Organization Unit attribute."""


class Photo(VCardProperty_BASE64EncodingParamNormalized):
    """An image or photograph of the individual associated with the vCard.
    It may point to an external URL or
    may be embedded in the vCard as a Base64 encoded block of text.
    """

    def denormalize(self, vcf_dict, version="2.1"):
        vcf_dict = super(Photo, self).denormalize(vcf_dict, version)
        if version == "2.1":
            for param in vcf_dict["parameters"][:]:
                if param[0].upper() == "VALUE":
                    vcf_dict["parameters"].remove(param)
        elif not version == "3.0":
            raise TypeError("unsupported version")
        return vcf_dict


class ProdID(VCardProperty):
    """The identifier for the product that created the vCard object."""


class Profile(VCardProperty):
    """States that the vCard is a vCard."""


class Rev(VCardProperty):
    """A timestamp for the last time the vCard was updated."""


class Role(VCardProperty):
    """The role, occupation, or business category of the vCard object within an organization."""


class SortString(VCardProperty):
    """Defines a string that should be used when an application sorts this vCard in some way."""


class Sound(VCardProperty_BASE64EncodingParamNormalized):
    """By default, if this property is not grouped with other properties
    it specifies the pronunciation of the FN property of the vCard object.
    It may point to an external URL or may be embedded in the vCard as
    a Base64 encoded block of text.
    """


class Source(VCardProperty):
    """A URL that can be used to get the latest version of this vCard."""


class Tel(VCardProperty_BASE64EncodingParamNormalized):
    """The canonical number string for a telephone number
    for telephony communication with the vCard object.
    """


class Title(VCardProperty_CharsetEncodingParamNormalized):
    """Specifies the job title, functional position or function of the individual
    associated with the vCard object within an organization.
    """


class TZ(VCardProperty):
    """The time zone of the vCard object."""


class UID(VCardProperty_CharsetEncodingParamNormalized):
    """Specifies a value that represents a persistent,
    globally unique identifier associated with the object.
    """


class URL(VCardProperty_CharsetEncodingParamNormalized):
    """A URL pointing to a website that represents the person in some way."""


class X_IRMC_CALL_DATETIME(VCardProperty_CharsetEncodingParamNormalized):
    """Call History extension
    The time of each call found in och, ich, mch and cch folder, can be shown using the
    IrMC [13] defined X-IRMC-CALL-DATETIME property that extends the vCard
    specification. This attribute can be used in combination with three newly created
    property parameters:
    - MISSED
    - RECEIVED
    - DIALED
    These are used to indicate the nature of the call that is time-stamped with X-IRMCCALL-DATETIME.

    For instance, a call that was missed on March 20th, 2005 at 10 am would be stamped:
    X-IRMC-CALL-DATETIME;MISSED:20050320T100000
    It is strongly recommended to use this property parameter whenever possible. They are
    especially useful in vCards that are retrieved from the cch folder ( see 3.1.2 ).
    Note that it is legal to use this property with no data ie,
    X-IRMC-CALL-DATETIME;MISSED:
    This scenario may occur if the device did not have the time/date set when the call was
    received. The phone number would be recorded but no date/time could be attached to it.
    It will still need to be added to the vCard as the cch log needs it to indicate the type of
    call that the record identifies.
    """


VCardProperties = {
    #############
    "BEGIN": Begin,
    "VERSION": Version,
    "N": N,
    "FN": FN,
    "END": End,
    #############
    "ADR": Adr,
    "AGENT": Agent,
    "BDAY": Birthday,
    "CATEGORIES": Categories,
    "CLASS": Class,
    "EMAIL": Email,
    "GEO": GEO,
    "IMPP": IMPP,
    "KEY": Key,
    "LABEL": Label,
    "LOGO": Logo,
    "MAILER": Mailer,
    "NAME": Name,
    "NICKNAME": Nickname,
    "NOTE": Note,
    "ORG": Org,
    "PHOTO": Photo,
    "PRODID": ProdID,
    "PROFILE": Profile,
    "REV": Rev,
    "ROLE": Role,
    "SORT-STRING": SortString,
    "SOUND": Sound,
    "SOURCE": Source,
    "TEL": Tel,
    "TITLE": Title,
    "TZ": TZ,
    "UID": UID,
    "URL": URL,
    ##############
    "X-IRMC-CALL-DATETIME": X_IRMC_CALL_DATETIME,
}
