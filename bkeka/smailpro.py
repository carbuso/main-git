import tempfile
import time
import re
import requests


class SMailProException(Exception):
    pass


class SMailPro(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.gmail_id = 0
        self.gmail_address = ''
        self.gmail_key = ''
        self.message_id = ''
        self.message_text = ''
        pass

    def get_email_address(self, gmail_id):
        # https://rapidapi.com/mrsonj/api/temp-gmail/endpoints
        # There are only 1000 real addresses as of today 2020-10-03
        if gmail_id < 1 or gmail_id > 1000:
            msg = ("SMailPro GMail id=%d outside range 1:1200" % gmail_id)
            print(msg)
            raise SMailProException(msg)
        # retain GMail id
        self.gmail_id = gmail_id

        url = "https://temp-gmail.p.rapidapi.com/get"
        querystring = {"id": str(self.gmail_id), "type": "real"}
        headers = { 'x-rapidapi-host': "temp-gmail.p.rapidapi.com",
                    'x-rapidapi-key': self.api_key}
        response = requests.request("GET", url, headers=headers, params=querystring)

        # {"code": 200, "msg": "OK", "items": {"username": "andea@gmail.com", "key": "5Ig.HU2Oc"}}
        deserialized = response.json()
        code = deserialized.get("code", 0)
        if code != 200:
            msg = ("SMailPro get email return code=%d is not 200" % code)
            print(msg)
            raise SMailProException(msg)

        items = deserialized.get("items")
        self.gmail_address = items.get("username")
        self.gmail_key = items.get("key")

        if "@gmail.com" not in self.gmail_address:
            msg = ("SMailPro generated address=%s is not from @gmail.com" % self.gmail_address)
            print(msg)
            raise SMailProException(msg)
        # Got GMail address
        return self.gmail_address

    def check_inbox(self):
        """Return value is: SUCCESS=0, ERROR !=0"""
        url = "https://temp-gmail.p.rapidapi.com/check"
        querystring = { "key": self.gmail_key, "username": self.gmail_address }
        headers = {'x-rapidapi-host': "temp-gmail.p.rapidapi.com",
                   'x-rapidapi-key': self.api_key}
        response = requests.request("GET", url, headers=headers, params=querystring)
        # {"code": 200, "msg": "OK",
        # "items": [ { "mid": "174c8f35932a", "textDate": "2020-09-26 12:46:53",
        #              "textFrom": "Smailpro", "textSubject": "Test", "textSnippet": "..."
        #             },
        #          ]
        deserialized = response.json()
        code = deserialized.get("code", 0)
        if code != 200:
            msg = ("SMailPro check inbox return code=%d is not 200" % code)
            print(msg)
            raise SMailProException(msg)

        items = deserialized.get("items")
        if len(items) == 0:
            return -1

        for it in items:
            # print(it)
            mid = it.get("mid")
            text_date = it.get("textDate")
            text_from = it.get("textFrom")
            text_subj = it.get("textSubject")
            text_snippet = it.get("textSnippet")
            # can run cross checks with sender address but not for now
            self.message_id = mid
            break
        # Got Email
        return 0

    def read_message(self):
        """Return value is: SUCCESS=0, ERROR !=0"""
        url = "https://temp-gmail.p.rapidapi.com/read"
        querystring = {"message_id": self.message_id, "username": self.gmail_address}
        headers = {'x-rapidapi-host': "temp-gmail.p.rapidapi.com",
                   'x-rapidapi-key': self.api_key}
        response = requests.request("GET", url, headers=headers, params=querystring)
        # {"code": 200, "msg": "OK", "items": { "body": "<div dir="ltr">Test<br></div>" } }
        deserialized = response.json()
        code = deserialized.get("code", 0)
        if code != 200:
            msg = ("SMailPro read email return code=%d is not 200" % code)
            print(msg)
            raise SMailProException(msg)

        items = deserialized.get("items")
        if len(items) == 0:
            return -1

        html_text = items.get("body")
        self.message_text = html_text
        return 0

    def get_last_message(self):
        return self.message_text


class SMailProManager(object):
    def __init__(self, api_key, email_id_range):
        self.smailpro = SMailPro(api_key)
        self.email_id_range = email_id_range
        self.email_id_min = 0
        self.email_id_max = 0
        # check "1:600" string format
        m = re.search('[\s]*([0-9]+)[\s]*:[\s]*([0-9]+)[\s]*', self.email_id_range)
        if m is not None and len(m.groups()) > 1:
            self.email_id_min = int(m.groups()[0].strip())
            self.email_id_max = int(m.groups()[1].strip())
        # check interval [min,max]
        if self.email_id_min >= self.email_id_max:
            msg = ("GMail min id=%d >= max id=%d" % (self.email_id_min, self.email_id_max))
            print(msg)
            raise SMailProException(msg)
        pass

    def get_email_address(self, email_id):
        # map id in the range
        id_range = self.email_id_max - self.email_id_min + 1
        id_beg = email_id % id_range
        new_id = self.email_id_min + id_beg
        return self.smailpro.get_email_address(new_id)

    def get_message_as_text(self):
        # check inbox for the message
        got_email = False
        for i in range(20):
            got_email = self.smailpro.check_inbox() == 0
            if got_email:
                break
            print("SMailPro waits 2s for the message")
            time.sleep(2)
        # did any message arrive?
        if not got_email:
            msg = "SMailPro did not get any message!"
            print(msg)
            raise SMailProException(msg)
        # return message as html
        if self.smailpro.read_message() == 0:
            html_text = self.smailpro.get_last_message()
            return html_text
        else:
            # could not read any message
            msg = "SMailPro could not read the message"
            print(msg)
            raise SMailProException(msg)

    def get_message_as_temp_file(self):
        # write the email to a temporary file that should be removed by caller
        html_content = self.get_message_as_text()
        html_file = ''
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            html_file = f.name
        with open(html_file, "w") as f:
            f.write(html_content)
        return html_file
