# pypbap
Python implementation of Phone Book Access Profile (PBAP) is a profile that allows exchange of Phone Book Objects between devices. It is likely to be used between a car kit and a mobile phone to:
* allow the car kit to display the name of the incoming caller;
* allow the car kit to download the phone book so the user can initiate a call from the car display

The profile consists of two roles:
* PSE - Phonebook Server Equipment for the side delivering phonebook data, like a mobile phone
* PCE - Phonebook Client Equipment, for the device receiving this data, like a personal navigation device

#### Installation
pypbap requires Linux and python2 to run.
```
$ cd pypbap
$ sudo python setup.py build
$ sudo python setup.py install
$ cd test/data
$ tar xavf phonebook_vfolder.tar.gz
```

#### Motivation
This python project is created to test the Phonebook Client Equipment (PCE) in CAR Infotainment system.
In general we use the real mobile phones to test Phonebook Client Equipment (PCE) in CAR Infotainment system, where it is hard to do reliability, stress and automated tests. Inorder to achieve that we have implemented the Phonebook Server Equipment (PSE) runs in linux platform.
We primarily need 'pbapserver' implementation, but we have implemented 'pbapclient' as well to make development easier.
This implementation is heavily rely on [pybluez](https://github.com/karulis/pybluez) and [pyobex](https://bitbucket.org/dboddie/pyobex) thanks to them!!

#### Usage Instructions 
Make sure the setup have two bluetooth adapters since loopback support is not available in bluetooth, we cannot run both client and server in same hardware.
```
$ hciconfig
hci1:   Type: BR/EDR  Bus: USB
    BD Address: 00:1A:7D:DA:71:05  ACL MTU: 310:10  SCO MTU: 64:8
    UP RUNNING PSCAN ISCAN
    RX bytes:7329 acl:134 sco:0 events:275 errors:0
    TX bytes:28619 acl:199 sco:0 commands:71 errors:0
hci0:   Type: BR/EDR  Bus: USB
    BD Address: F8:16:54:86:11:FD  ACL MTU: 1021:5  SCO MTU: 96:5
    UP RUNNING PSCAN ISCAN
    RX bytes:73576 acl:553 sco:0 events:1472 errors:0
    TX bytes:39635 acl:488 sco:0 commands:421 errors:0
```

Start the server on one of the bluetooth address.
```
$ cd pypbap
$ python pbapserver.py --address 00:1A:7D:DA:71:05 --use-fs --rootdir test/data/phonebook_vfolder
Starting server for 00:1A:7D:DA:71:05 on port 1
....
```

Start the client by specifying server's bluetooth address.
```
$ cd pypbap
$ python pbapclient.py 
Welcome to the PhoneBook Access Profile!
pbap> connect 00:1A:7D:DA:71:05
2018-02-08 11:36:34,172 __main__ INFO     Finding PBAP service ...
2018-02-08 11:36:35,442 __main__ INFO     PBAP service found!
2018-02-08 11:36:35,442 __main__ INFO     Connecting to pbap server = (00:1A:7D:DA:71:05, 1)
2018-02-08 11:36:36,437 __main__ INFO     Connect success

pbap> pull_vcard_listing telecom/pb
2018-02-08 12:03:27,157 __main__ INFO     Requesting pull_vcard_listing with parameters {'name': 'telecom/pb', 'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>, 'list_startoffset': 0, 'search_value': None, 'search_attribute': 0, 'order': 0, 'max_list_count': 65535}
2018-02-08 12:03:40,896 __main__ INFO     Result of pull_vcard_listing:
<?xml version="1.0"?>
<!DOCTYPE vcard-listing SYSTEM "vcard-listing.dtd">
<vCard-listing version="1.0">
<card handle="0.vcf" name="Bolt;Usain;;;"/>
<card handle="1.vcf" name="Sanvi;Nithisha;;;"/>
<card handle="2.vcf" name=";Raja;;;"/>
<card handle="3.vcf" name="kumar;manoj;;;"/>
<card handle="4.vcf" name="Jason Momoa"/>
<card handle="5.vcf" name="Akira Kurosawa"/>
<card handle="6.vcf" name="Fan Bingbing"/>
<card handle="7.vcf" name="Rajnikanth"/>
<card handle="8.vcf" name="Deepika Padukone"/>
<card handle="9.vcf" name="Tom Hardy"/>
</vCard-listing>

pbap> set_phonebook telecom/pb
2018-02-08 12:03:51,785 __main__ INFO     Setting current folder with params '{'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>, 'to_root': False, 'name': 'telecom/pb', 'to_parent': False}'
2018-02-08 12:03:52,064 __main__ INFO     Result of set_phonebook:
<PyOBEX.responses.Success instance at 0x7f3f41b5d170>

pbap> pull_vcard_entry 2.vcf
2018-02-08 12:03:56,473 __main__ INFO     Requesting pull_vcard_entry for pbobject with parameters {'filter_': 0, 'format_': 0, 'name': '2.vcf', 'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>}
2018-02-08 12:03:56,780 __main__ INFO     Result of pull_vcard_entry:
BEGIN:VCARD
VERSION:2.1
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:;Raja;;;
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Raja
TEL;CELL:+029384590
EMAIL;PREF;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:raja@gmail.com
URL;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:http://www.google.com/profiles/106958240871125503740123412
END:VCARD

pbap> set_phonebook --to-parent
2018-02-08 12:45:05,031 __main__ INFO     Setting current folder with params '{'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>, 'to_root': False, 'name': '', 'to_parent': True}'
2018-02-08 12:45:05,387 __main__ INFO     Result of set_phonebook:
<PyOBEX.responses.Success instance at 0x7f3f41df0d88>

pbap> set_phonebook --to-parent
2018-02-08 12:45:06,096 __main__ INFO     Setting current folder with params '{'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>, 'to_root': False, 'name': '', 'to_parent': True}'
2018-02-08 12:45:06,124 __main__ INFO     Result of set_phonebook:
<PyOBEX.responses.Success instance at 0x7f3f41b000e0>

pbap> pull_phonebook telecom/ich.vcf
2018-02-08 12:45:51,171 __main__ INFO     Requesting pull_phonebook for pbobject 'telecom/ich.vcf' with appl parameters {'name': 'telecom/ich.vcf', 'self': <__main__.PBAPClient instance at 0x7f3f41af1a70>, 'list_startoffset': 0, 'filter_': 0, 'format_': 0, 'max_list_count': 65535}
2018-02-08 12:45:51,545 __main__ INFO     Result of pull_phonebook:
BEGIN:VCARD
VERSION:2.1
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Jason=20Momoa
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Jason=20Momoa
TEL;CELL:+491512541234
X-IRMC-CALL-DATETIME;RECEIVED;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:20170317T173147
END:VCARD
BEGIN:VCARD
VERSION:2.1
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Akira=20Kurosawa
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Akira=20Kurosawa
TEL;CELL:+8115163093403
X-IRMC-CALL-DATETIME;RECEIVED;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:20170315T112738
END:VCARD
BEGIN:VCARD
VERSION:2.1
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Fan=20Bingbing
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Fan=20Bingbing
TEL;CELL:+8615163252823
X-IRMC-CALL-DATETIME;RECEIVED;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:20170314T173942
END:VCARD

pbap> disconnect
2018-02-08 12:46:15,674 __main__ DEBUG    Disconnecting pbap client with pbap server
pbap> quit
```

#### Additional information
* Using 'pbapclient' we can test the 'pbapserver' in mobile phones also. ('mirror_vfolder' cmd in 'pbapclient' would download the entire phonebook from your phone, nice to playaround with).
* Instead of using filesystem as storage, we can even serve the phonebook from mongodb which would give you more control over manipulating the phonebook data (will save lot of time while writing automated tests). Will update more tools and documentation about this soon.
* Implementation done adhering to pbap v1.1

#### License
Code is licensed under the GPL-3.0 (Look into License.txt for more information)
