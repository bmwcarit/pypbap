# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Virtual Folder Architecture implementation for Phone Book Access Profile"""

import os

from abc import ABCMeta, abstractmethod
from pymongo import MongoClient
from six import with_metaclass
from vcard_helper import VCard


class VFolderPhoneBook(with_metaclass(ABCMeta, object)):
    """Abstract PhoneBook VirtualFolder class"""

    def __init__(self, rootdir="/"):
        self.rootdir = self.curdir = rootdir

    @abstractmethod
    def exists(self, path):
        """Checks the given path exists in Phonebook virtual folder"""
        pass

    @abstractmethod
    def isdir(self, path):
        """Checks whether given path is directory or not"""
        pass

    @abstractmethod
    def isfile(self, path):
        """Checks whether given path is file or not"""
        pass

    def join(self, *args):
        """wrapper around os.path.join"""
        return os.path.abspath(os.path.join(*args))

    @abstractmethod
    def makedirs(self, path):
        """creates directory in path if not exists"""
        pass

    @abstractmethod
    def listdir(self, path):
        """Lists the directory content of phonebook folder"""
        pass

    @abstractmethod
    def read(self, path):
        """Returns the content of the phonebook object"""
        pass

    @abstractmethod
    def chdir(self, path):
        """Changes the current directory in phonebook's virtual folder"""
        pass

    @abstractmethod
    def count(self, path):
        """Returns the count of number of object in phonebook folder"""
        pass


class VFolderPhoneBook_DB(VFolderPhoneBook):
    """Virtual Folder Phonebook class backed by MongoDB as storage"""

    def __init__(self, rootdir="/"):
        super(VFolderPhoneBook_DB, self).__init__(rootdir)
        self.dbclient = MongoClient()
        self.curdb = self.dbclient.phone_memory

    def exists(self, path):
        if path in ["/", "/telecom", "/SIM1/", "/SIM1/telecom"]:
            return True
        db, coll = self._path_to_db_elements(path)
        return coll in db.collection_names()

    def isdir(self, path):
        if path.endswith(".vcf"):
            return False
        return self.exists(path)

    def isfile(self, path):
        if not path.endswith(".vcf") or not self.exists(path):
            return False
        index = os.path.basename(path).split(".")[0]
        if self._is_phonebook_object(index):
            return True
        db, coll = self._path_to_db_elements(path)
        return int(index) < db[coll].count()

    def makedirs(self, path):
        if self.exists(path):
            return False
        else:
            db, coll = self._path_to_db_elements(path)
            return db.create_collection(coll)

    def listdir(self, path, query={}, projection={"_id": False}, sort=("_id", 1)):
        if not self.isdir(path):
            raise RuntimeError("Specified path {path} is not a directory.".format(path=path))
        else:
            db, coll = self._path_to_db_elements(path)
            return list(db[coll].find(query, projection).sort(*sort))

    def read(self, path, query={}, projection={"_id": False}, sort=("_id", 1)):
        if not self.isfile(path):
            raise RuntimeError("Specified path {path} is not a file".format(path=path))
        else:
            vcard_index = int(os.path.splitext(os.path.basename(path))[0])
            db, coll = self._path_to_db_elements(path)
            return db[coll].find(query, projection).sort(*sort).skip(vcard_index).limit(1).next()

    def chdir(self, path):
        if not self.exists(path):
            raise RuntimeError("Specified path {path} not found.".format(path=path))
        self.curdir = os.path.abspath(path)
        return self._path_to_db_elements(self.curdir)

    def count(self, path):
        if not self.isdir(path):
            raise RuntimeError("Specified path {path} is not a directory.".format(path=path))
        else:
            db, coll = self._path_to_db_elements(path)
            return db[coll].count()

    def _path_to_db_elements(self, path):
        """if you give current path, this will return (database, collection)"""
        if "SIM" in path or "SIM" in self.curdir:
            self.curdb = self.dbclient.sim_memory
        else:
            self.curdb = self.dbclient.phone_memory
        if path.endswith(".vcf"):
            index = os.path.basename(path).split(".")[0]
            if self._is_phonebook_object(index):
                collection = index
            else:
                collection = os.path.basename(os.path.dirname(path))
        else:
            collection = os.path.basename(path)
        return (self.curdb, collection)

    def _is_phonebook_object(self, name):
        return name in ["pb", "mch", "ich", "och", "cch", "spd", "fav"]


class VFolderPhoneBook_FS(VFolderPhoneBook):
    """Virtual Folder Phonebook class backed by FileSystem as storage"""

    def __init__(self, rootdir=os.path.join(os.getcwd(), "phonebook_vfolder")):
        super(VFolderPhoneBook_FS, self).__init__(os.path.abspath(rootdir))

    def exists(self, path):
        """Checks the given path exists in Phonebook virtual folder"""
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        return os.path.exists(abspath)

    def isdir(self, path):
        """Checks whether given path is directory or not"""
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        return os.path.isdir(abspath)

    def isfile(self, path):
        """Checks whether given path is file or not"""
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        return os.path.isfile(abspath)

    def makedirs(self, path):
        """creates directory in path if not exists"""
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        os.makedirs(abspath)

    def listdir(self, path, query={}, projection={"_id": False}, sort=("_id", 1)):
        """Lists the directory content of phonebook folder"""
        if not self.isdir(path):
            raise ValueError("Give path {} is not a directory".format(path))
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        dir_contents = []
        # TODO: Need to add sort, project, query functionalities
        for pb_object in sorted(os.listdir(abspath), key=lambda x: int(os.path.splitext(x)[0])):
            vcard_dict = VCard(open(os.path.join(abspath, pb_object)).read(), parsed=False).to_dict()
            dir_contents.append(vcard_dict)
        return dir_contents

    def read(self, path, query={}, projection={"_id": False}, sort=("_id", 1)):
        """Returns the content of the phonebook object"""
        if not self.isfile(path):
            raise ValueError("Give path {} is not a file".format(path))
        # TODO: Need to add sort, project, query functionalities
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        return VCard(open(abspath).read(), parsed=False).to_dict()

    def chdir(self, path):
        """Changes the current directory in phonebook's virtual folder"""
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        self.curdir = abspath

    def count(self, path):
        """Returns the count of number of object in phonebook folder"""
        if not self.isdir(path):
            raise ValueError("Give path {} is not a directory".format(path))
        abspath = os.path.abspath(os.path.join(self.curdir, path))
        return len(os.listdir(abspath))
