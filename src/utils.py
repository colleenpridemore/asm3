#!/usr/bin/python

import al
import codecs
import configuration
import csv as extcsv
import datetime
import db
import hashlib
import htmlentitydefs
import re
import smtplib
import sys
import thread
import urllib2
import users
import web
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email import Charset, Encoders
from i18n import _, display2python
from cStringIO import StringIO
from sitedefs import SMTP_SERVER, FROM_ADDRESS

# Monkeypatch to allow SNI support in urllib3. This is necessary
# as many servers (including Facebook and PetLink)
# will not allow us to connect and use HTTPS without SNI
try:
    import requests
    from urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()
except:
    sys.stderr.write("No requests/urllib3 module found.")

# Global reference to the Python websession. This is used to allow
# debug mode with webpy by keeping a global single copy of the
# session (in debug mode, module reloading means you'd create two
# session objects)
websession = None

class PostedData(object):
    """
    Helper class for reading fields from the web.py web.input object
    and doing type coercion.
    """
    data = None
    locale = None
    def __init__(self, data, locale):
        self.data = data
        self.locale = locale
    def boolean(self, field):
        return df_kc(self.data, field)
    def db_boolean(self, field):
        return df_c(self.data, field)
    def date(self, field):
        return df_kd(self.data, field, self.locale)
    def datetime(self, datefield, timefield):
        return df_kdt(self.data, datefield, timefield, self.locale)
    def db_date(self, field):
        return df_d(self.data, field, self.locale)
    def db_datetime(self, datefield, timefield):
        return df_dt(self.data, datefield, timefield, self.locale)
    def integer(self, field):
        return df_ki(self.data, field)
    def db_integer(self, field):
        return df_s(self.data, field)
    def integer_list(self, field):
        return df_kl(self.data, field)
    def floating(self, field):
        return df_kf(self.data, field)
    def db_floating(self, field):
        return str(df_kf(self.data, field))
    def string(self, field):
        return df_ks(self.data, field)
    def db_string(self, field):
        return df_t(self.data, field)
    def filename(self):
        if self.data.has_key("filechooser"):
            return encode_html(self.data.filechooser.filename)
        return ""
    def filedata(self):
        if self.data.has_key("filechooser"):
            return self.data.filechooser.value
        return ""
    def __contains__(self, key):
        return self.data.has_key(key)
    def has_key(self, key):
        return self.data.has_key(key)
    def __getitem__(self, key):
        return self.string(key)
    def __repr__(self):
        x = []
        for k,v in self.data.iteritems():
            x.append("%s:%s" % (k, v.encode("ascii", "xmlcharrefreplace")))
        return ", ".join(x)

def is_numeric(s):
    """
    Returns true if the string s is a number
    """
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True

def atoi(s):
    """
    Converts only the numeric portion of a string to an integer
    """
    x = re.findall('\d+', s)
    if x is None or len(x) == 0: return 0
    return cint(x[0])

def cint(s):
    """
    Converts a string to an int, coping with None and non-int values
    """
    try:
        return int(s)
    except:
        return 0

def cfloat(s):
    """
    Converts a string to a float, coping with None and non-numeric values
    """
    try:
        return float(s)
    except:
        return float(0)

def nulltostr(s):
    try:
        if s is None: return ""
        if type(s) == unicode:
            s = s.encode("ascii", "xmlcharrefreplace")
        return str(s)
    except:
        em = "[" + str(sys.exc_info()[0]) + "]"
        return em

def filename_only(filename):
    """ If a filename has a path, return just the name """
    if filename.find("/") != -1: filename = filename[filename.rfind("/")+1:]
    if filename.find("\\") != -1: filename = filename[filename.rfind("\\")+1:]
    return filename

def address_first_line(address):
    """
    Returns the first line of an address
    """
    if address is None: return ""
    bits = address.split("\n")
    if len(bits) > 0:
        return bits[0]
    return ""

def address_house_number(address):
    """
    Returns the house number from an address
    """
    fl = address_first_line(address)
    if fl == "": return ""
    bits = fl.split(" ")
    if is_numeric(bits[0]):
        return bits[0]
    return ""

def address_street_name(address):
    """
    Returns the street name from an address line
    """
    fl = address_first_line(address)
    if fl == "": return ""
    bits = fl.split(" ", 1)
    if len(bits) == 2:
        return bits[1]
    return ""

def spaceleft(s, spaces):
    """
    leftpads a string to a number of spaces
    """
    sp = "                                                 "
    if len(s) > spaces: return s
    nr = spaces - len(s)
    return sp[0:nr] + s

def spaceright(s, spaces):
    """
    rightpads a string to a number of spaces
    """
    sp = "                                                 "
    if len(s) > spaces: return s
    nr = spaces - len(s)
    return s + sp[0:nr]

def padleft(num, digits):
    """
    leftpads a number to digits
    """
    zeroes = "000000000000000"
    s = str(num)
    if len(s) > digits: return s
    nr = digits - len(s)
    return zeroes[0:nr] + s

def padright(num, digits):
    """
    rightpads a number to digits
    """
    zeroes = "000000000000000"
    s = str(num)
    if len(s) > digits: return s
    nr = digits - len(s)
    return s + zeroes[0:nr]

def truncate(s, length = 100):
    """
    Truncates a string to length. If the string is longer than
    length, appends ...
    Removes any unicode sequences
    HTML entities count as one character
    """
    if s is None: s = ""
    s = strip_html_tags(s)
    s = strip_unicode(s)
    if len(decode_html(s)) < length: return s
    return substring(s, 0, length) + "..."

def substring(s, start, end = None):
    """
    Returns a substring. If s contains any HTML/unicode escape sequences, they
    are evaluated and count as one char.
    """
    us = decode_html(s)
    if end is None or end > len(us):
        ur = us[start:]
    else:
        ur = us[start:end]
    return ur.encode("ascii", "xmlcharrefreplace")

def strip_html_tags(s):
    """
    Removes all html tags from a string, leaving just the
    content behind.
    """
    return re.sub('<.*?>', '', s)

def strip_unicode(s):
    """
    Remove any unicode characters
    """
    return "".join(i for i in s if ord(i)<128)

def decode_html(s):
    """
    Decodes HTML entities and returns a unicode string.
    """
    # It's empty, return an empty string
    if s is None: return ""
    # It's not a string, we can't deal with this
    if not isinstance(s, str): return s
    matches = re.findall("&#\d+;", s)
    if len(matches) > 0:
        hits = set(matches)
        for hit in hits:
            name = hit[2:-1]
            try:
                entnum = int(name)
                s = s.replace(hit, unichr(entnum))
            except ValueError:
                pass
    matches = re.findall("&#[xX][0-9a-fA-F]+;", s)
    if len(matches) > 0:
        hits = set(matches)
        for hit in hits:
            hexv = hit[3:-1]
            try:
                entnum = int(hexv, 16)
                s = s.replace(hit, unichr(entnum))
            except ValueError:
                pass
    matches = re.findall("&\w+;", s)
    hits = set(matches)
    amp = "&amp;"
    if amp in hits:
        hits.remove(amp)
    for hit in hits:
        name = hit[1:-1]
        if htmlentitydefs.name2codepoint.has_key(name):
            s = s.replace(hit, unichr(htmlentitydefs.name2codepoint[name]))
    s = s.replace(amp, "&")
    return s

def encode_html(s):
    """
    Encodes Unicode strings as HTML entities in an ASCII string
    """
    if s is None: return ""
    if type(s) == str: 
        return unicode(s, "utf8").encode("ascii", "xmlcharrefreplace")
    else:
        return s.encode("ascii", "xmlcharrefreplace")

def html_to_uri(s):
    """
    Converts HTML escaped entities to URI escaping.
    &#256; -> %ff%01
    """
    for ent in re.findall("&#(\d+?);", s):
        h = "%04x" % cint(ent)
        s = s.replace("&#" + ent + ";", "%" + h[0:2] + "%" + h[2:4])
    return s

def list_overlap(l1, l2):
    """
    Returns True if any of the items in l1 are present in l2.
    """
    for l in l1:
        if l in l2:
            return True
    return False

class ASMValidationError(web.HTTPError):
    """
    Custom error thrown by data modules when validation fails
    """
    def __init__(self, msg):
        status = '500 %s' % msg
        headers = { 'Content-Type': "text/html" }
        data = "<h1>Validation Error</h1><p>%s</p>" % msg
        web.HTTPError.__init__(self, status, headers, data)

class ASMPermissionError(web.HTTPError):
    """
    Custom error thrown by data modules when validation fails
    """
    def __init__(self, msg):
        status = '500 %s' % msg
        headers = { 'Content-Type': "text/html" }
        data = "<h1>Permission Error</h1><p>%s</p>" % msg
        web.HTTPError.__init__(self, status, headers, data)

class ASMError(web.HTTPError):
    """
    Custom error thrown by data modules 
    """
    def __init__(self, msg):
        status = '500 %s' % msg
        headers = { 'Content-Type': "text/html" }
        data = "<h1>Error</h1><p>%s</p>" % msg
        web.HTTPError.__init__(self, status, headers, data)

def df_c(data, field):
    """ Returns a checkbox field for the database """
    if not data.has_key(field): 
        return db.di(0)
    if data[field] == "checked" or data[field] == "on":
        return db.di(1)
    else:
        return db.di(0)

def df_t(data, field):
    """ Returns a posted text field for the database, turns it from unicode into
        ascii with XML entities to represent codepoints > 128 """
    if data.has_key(field):
        if type(data[field]) == str: 
            s = unicode(data[field], "utf8").encode("ascii", "xmlcharrefreplace")
        else:
            s = data[field].encode("ascii", "xmlcharrefreplace")
        return db.ds(s.strip())
    else:
        return "''"

def df_s(data, field):
    """ Returns a select field for the database """
    if data.has_key(field):
        return db.di(data[field])
    else:
        return "0"

def df_d(data, field, l):
    """ Returns a date field for the database """
    if data.has_key(field):
        return db.dd(display2python(l, data[field]))
    else:
        return "Null"

def df_dt(data, datefield, timefield, l):
    """ Returns a datetime field for the database """
    return db.ddt(df_kdt(data, datefield, timefield, l))

def df_kc(data, field):
    """ Returns a checkbox field """
    if not data.has_key(field): 
        return 0
    if data[field] == "checked" or data[field] == "on":
        return 1
    else:
        return 0

def df_ki(data, field):
    """ Returns an integer key from a datafield """
    if data.has_key(field):
        return cint(data[field])
    else:
        return 0

def df_kf(data, field):
    """ Returns a float key from a datafield """
    if data.has_key(field):
        return cfloat(data[field])
    else:
        return float(0)

def df_ks(data, field):
    """ Returns a string key from a datafield """
    if data.has_key(field):
        s = encode_html(data[field])
        return s.strip()
    else:
        return ""

def df_kd(data, field, l):
    """ Returns a date key from a datafield """
    if data.has_key(field):
        return display2python(l, data[field])
    else:
        return None

def df_kdt(data, datefield, timefield, l):
    """ Returns a datetime field """
    if data.has_key(datefield):
        d = display2python(l, data[datefield])
        if d is None: return None
        if data.has_key(timefield):
            tbits = data[timefield].split(":")
            hour = 0
            minute = 0
            second = 0
            if len(tbits) > 0:
                hour = cint(tbits[0])
            if len(tbits) > 1:
                minute = cint(tbits[1])
            if len(tbits) > 2:
                second = cint(tbits[2])
            t = datetime.time(hour, minute, second)
            d = d.combine(d, t)
        return d
    else:
        return None

def df_kl(data, field):
    """
    Returns a list of integers from a datafield that contains
    comma separated numbers.
    """
    if data.has_key(field):
        s = df_ks(data, field)
        items = s.split(",")
        ids = []
        for i in items:
            if is_numeric(i):
                ids.append(cint(i))
        return ids
    else:
        return []

def escape_tinymce(content):
    """
    Escapes HTML content for placing inside a tinymce
    textarea. Basically, just the < and > markers - other
    escaped tokens should be left for the browser to
    expand - except &gt; and &lt; for our << >> markers
    (god this is confusing), which need to be double
    escaped or tinymce breaks. 
    """
    c = content.replace("&gt;", "&amp;gt;")
    c = c.replace("&lt;", "&amp;lt;")
    c = c.replace("<", "&lt;")
    c = c.replace(">", "&gt;")
    return c

class UnicodeCSVWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, dialect=extcsv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = extcsv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        outbuf = []
        for s in row:
            if isinstance(s, unicode):
                outbuf.append(s.encode("utf-8"))
            else:
                outbuf.append(s)
        self.writer.writerow(outbuf)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def csv(rows, cols = None, includeheader = True):
    """
    Creates a CSV file from a set of resultset rows. If cols has been 
    supplied as a list of strings, fields will be output in that
    order.
    """
    if rows is None or len(rows) == 0: return ""
    strio = StringIO()
    out = UnicodeCSVWriter(strio)
    if cols is None:
        cols = []
        for k, v in rows[0].iteritems():
            cols.append(k)
        cols = sorted(cols)
    if includeheader: 
        out.writerow(cols)
    for r in rows:
        rd = []
        for c in cols:
            rd.append(decode_html(r[c]))
        out.writerow(rd)
    return strio.getvalue()

def fix_relative_document_uris(s, baseurl, account = "" ):
    """
    Switches the relative uris used in document templates for absolute
    ones to the service so that documents will work outside of 
    the ASM UI.
    """
    if account != "":
        account = "&account=" + account
    s = s.replace("image?mode=animal&amp;id=", baseurl + "/service?method=animal_image" + account + "&animalid=")
    s = s.replace("image?mode=dbfs&amp;id=/reports/", baseurl + "/service?method=extra_image" + account + "&title=")
    return s

def substitute_tags(searchin, tags, use_xml_escaping = True, opener = "&lt;&lt;", closer = "&gt;&gt;"):
    """
    Substitutes the dictionary of tags in "tags" for any found
    in "searchin". opener and closer denote the start of a tag,
    if use_xml_escaping is set to true, then tags are XML escaped when
    output and opener/closer are escaped.
    """
    if not use_xml_escaping:
        opener = opener.replace("&lt;", "<").replace("&gt;", ">")
        closer = closer.replace("&lt;", "<").replace("&gt;", ">")

    s = searchin
    sp = s.find(opener)
    while sp != -1:
        ep = s.find(closer, sp + len(opener))
        if ep != -1:
            matchtag = s[sp + len(opener):ep].upper()
            newval = ""
            if tags.has_key(matchtag):
                newval = tags[matchtag]
                if newval is not None:
                    newval = str(newval)
                    if use_xml_escaping and not newval.lower().startswith("<img"):
                        newval = newval.replace("&", "&amp;")
                        newval = newval.replace("<", "&lt;")
                        newval = newval.replace(">", "&gt;")
            s = s[0:sp] + str(newval) + s[ep + len(closer):]
            sp = s.find(opener, sp)
        else:
            # No end marker for this tag, stop processing
            break
    return s

def check_locked_db(session):
    if session.dbo.locked: 
        l = session.locale
        raise ASMPermissionError(_("This database is locked.", l))

def check_loggedin(session, web, loginpage = "/login"):
    """
    Checks if we have a logged in user and if not, redirects to
    the login page
    """
    if not is_loggedin(session):
        path = web.ctx.path
        if path.startswith("/"): path = path[1:]
        query = str(web.ctx.query)
        raise web.seeother(loginpage + "?target=" + path + query)

def is_loggedin(session):
    """
    Returns true if the user is logged in
    """
    return session.has_key("user") and session.user is not None

def md5_hash(s):
    """
    Returns an md5 hash of a string
    """
    m = hashlib.md5()
    m.update(s)
    s = m.hexdigest()
    return s

def where_text_filter(dbo, field, term):
    """
    Used when adding a text search term filter to a where clause. It matches
    the lowered string literally, decodes the search term to unicode and matches for
    that.
    dbo: The database info
    field: The field we're filtering on
    term:  The item we're filtering for
    """
    normal = u"LOWER(%s) LIKE '%%%s%%'" % (field, term.lower())
    decoded = u"LOWER(%s) LIKE  '%%%s%%'" % (field, decode_html(term.lower()))
    wc = normal + u" OR " + decoded
    dummy = dbo.dbtype
    # postdec can't work - we can have postgresql decode the html entities before
    # comparison like this, but LOWER/UPPER rely on the collation order being set
    # correctly, so if we have a language with a different charset, (this was done for 
    # cyrillic originally), then UPPER and LOWER won't work as they're comparing for
    # English and the only way to switch to cyrillic in PostgreSQL 8.x is for the whole 
    # cluster.
    # TODO: This is something we can revisit when we are using PostgreSQL 9.1 or better
    #       as it allows you to specify collation in queries with the locale, 
    #       eg: select a COLLATE "fr_FR"
    # TODO: Another way to fix it is to have a lookup table of lowercase characters for
    #       every cyrillic (or other charset) character and to replace those when
    #       comparing. Not very efficient or realistic, case insensitive searching is
    #       something we can't support in non-Latin alphabets at present.
    #if dbo.dbtype == "POSTGRESQL" and not dbo.locale.startswith("en"):
    #    postdec = u"LOWER(((xpath('/z/text()', ('<z>' || %s || '</z>')::xml))[1])::varchar) LIKE LOWER('%%%s%%')" % (field, decode_html(term))
    #    wc += u" OR " + postdec
    return wc

def get_url(url, headers = {}, cookies = {}):
    """
    Retrieves a URL
    return value is headers and response as a string
    """
    r = requests.get(url, headers = headers, cookies=cookies)
    return { "cookies": r.cookies, "headers": r.headers, "response": r.text, "status": r.status_code, "requestheaders": r.request.headers, "requestbody": r.request.body }

def post_form(url, fields, headers = {}, cookies = {}):
    """
    Does a form post
    url: The http url to post to
    fields: A map of { name: value } elements
    headers: A map of { name: value } headers
    return value is the http headers (a map) and server's response as a string
    """
    r = requests.post(url, data=fields, headers=headers, cookies=cookies)
    return { "cookies": r.cookies, "headers": r.headers, "response": r.text, "status": r.status_code, "requestheaders": r.request.headers, "requestbody": r.request.body }

def post_multipart(url, fields, files, headers = {}, cookies = {}):
    """
    Does a multipart form post
    url: The http url to post to
    files: A map of { name: (name, data, mime) }
    fields: A map of { name: value } elements
    headers: A map of { name: value } headers
    return value is the http headers (a map) and server's response as a string
    """
    r = requests.post(url, files=files, data=fields, headers=headers, cookies=cookies)
    return { "cookies": r.cookies, "headers": r.headers, "response": r.text, "status": r.status_code, "requestheaders": r.request.headers, "requestbody": r.request.body }

def post_xml(url, xml, headers = {}):
    """
    Posts an XML document to a URL
    """
    headers["Content-Type"] = "text/xml"
    req = urllib2.Request(url, xml, headers)
    resp = urllib2.urlopen(req)
    return { "headers": resp.info().headers, "response": resp.read(), "status": resp.getcode() }

def send_email(dbo, replyadd, toadd, ccadd = "", subject = "", body = "", contenttype = "plain", attachmentdata = None, attachmentfname = ""):
    """
    Sends an email.
    fromadd is an RFC821 address
    toadd is a comma separated list of RFC821 addresses
    ccadd is a comma separated list of RFC821 addresses
    subject, body are strings
    contenttype is either "plain" or "html"
    attachmentdata: If an attachment should be added, the unencoded data
    attachmentfname: If an attachment should be added, the file name to give it
    returns True on success
    """
    def parse_email(s):
        # Returns a tuple of description and address
        s = s.strip()
        fp = s.find("<")
        ep = s.find(">")
        description = s
        address = s
        if fp != -1 and ep != -1:
            description = s[0:fp].strip()
            address = s[fp+1:ep].strip()
        return (description, address)

    def strip_email(s):
        # Just returns the address portion of an email
        description, address = parse_email(s)
        return address

    def add_header(msg, header, value):
        # Adds a header to the message, expands any HTML entities
        # and re-encodes as utf-8 before adding to the message if necessary.
        # If the message doesn't contain HTML entities, then it is just
        # added normally as 7-bit ascii
        if value.find("&#") != -1:
            # Is this, To/From/Cc ? If so, parse the addresses and 
            # encode the descriptions
            if header == "To" or header == "From" or header == "Cc":
                addresses = value.split(",")
                newval = ""
                for a in addresses:
                    description, address = parse_email(a)
                    if newval != "": newval += ", "
                    newval += "\"%s\" <%s>" % (Header(decode_html(description).encode("utf-8"), "utf-8"), address)
                msg[header] = newval
            else:
                h = Header(decode_html(value).encode("utf-8"), "utf-8")
                msg[header] = h
        else:
            msg[header] = value

    # If the email is plain text, but contains HTML escape characters, 
    # switch it to being an html message instead and make sure line 
    # breaks are retained
    if body.find("&#") != -1 and contenttype == "plain":
        contenttype = "html"
        body = body.replace("\n", "<br />")
        Charset.add_charset("utf-8", Charset.QP, Charset.QP, "utf-8")

    # Build the from address from our sitedef
    fromadd = FROM_ADDRESS
    fromadd = fromadd.replace("{organisation}", configuration.organisation(dbo))
    fromadd = fromadd.replace("{alias}", dbo.alias)
    fromadd = fromadd.replace("{database}", dbo.database)

    # Construct the mime message
    msg = MIMEMultipart()
    msgtext = MIMEText(body, contenttype)
    add_header(msg, "From", fromadd)
    add_header(msg, "Reply-To", replyadd)
    add_header(msg, "To", toadd)
    if ccadd != "": 
        add_header(msg, "Cc", ccadd)
    add_header(msg, "Subject", subject)
    msg.attach(msgtext)

    # If an attachment has been specified, add it to the message
    if attachmentdata is not None:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( attachmentdata )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % attachmentfname)
        msg.attach(part)
     
    # Grab the server config
    server = ""
    username = ""
    password = ""
    usetls = False
    if SMTP_SERVER is None:
        server = configuration.smtp_server(dbo)
        username = configuration.smtp_server_username(dbo)
        password = configuration.smtp_server_password(dbo) 
        usetls = configuration.smtp_server_tls(dbo)
    else:
        server = SMTP_SERVER["host"]
        username = SMTP_SERVER["username"]
        password = SMTP_SERVER["password"]
        usetls = SMTP_SERVER["usetls"]
     
    # Construct the list of to addresses
    tolist = [strip_email(x) for x in toadd.split(",")]
    if ccadd != "":
        tolist += [strip_email(x) for x in ccadd.split(",")]

    try:
        smtp = smtplib.SMTP(server)
        if usetls:
            smtp.starttls()
        if password.strip() != "":
            smtp.login(username, password)
        replyadd = strip_email(replyadd)
        al.debug("from: %s, reply-to: %s, to: %s, subject: %s, body: %s" % \
            (fromadd, replyadd, str(tolist), subject, body), "utils.send_email", dbo)
        smtp.sendmail(fromadd, tolist, msg.as_string())
        return True
    except Exception,err:
        al.error("%s" % str(err), "utils.send_email", dbo)
        return False

def send_bulk_email(dbo, fromadd, subject, body, rows, contenttype):
    """
    Sends a set of bulk emails asynchronously.
    fromadd is an RFC821 address
    subject and body are strings. Either can contain <<TAGS>>
    rows is a list of dictionaries of tag tokens with real values to substitute
    contenttype is either "plain" or "html"
    """
    def do_send():
        for r in rows:
            ssubject = substitute_tags(subject, r, False, opener = "<<", closer = ">>")
            sbody = substitute_tags(body, r, False, opener = "<<", closer = ">>")
            toadd = r["EMAILADDRESS"]
            if toadd is None or toadd.strip() == "": continue
            al.debug("sending bulk email: to=%s, subject=%s" % (toadd, ssubject), "utils.send_bulk_email", dbo)
            send_email(dbo, fromadd, toadd, "", ssubject, sbody, contenttype)
    thread.start_new_thread(do_send, ())

def send_user_email(dbo, sendinguser, user, subject, body):
    """
    Sends an email to users.
    sendinguser: The username of the person sending the email (we will look up their email)
    user:        can be an individual username, a rolename or the translated 
                 version of (all) or (everyone) to denote all users.
    """
    l = dbo.locale
    DEFAULT_EMAIL = "noreply@sheltermanager.com"
    sendinguser = users.get_users(dbo, sendinguser)
    if len(sendinguser) == 0:
        fromadd = DEFAULT_EMAIL
    else:
        fromadd = sendinguser[0]["EMAILADDRESS"]
        if fromadd is None or fromadd.strip() == "":
            fromadd = DEFAULT_EMAIL
    allusers = users.get_users(dbo)
    for u in allusers:
        # skip if we have no email address - we can't send it.
        if u["EMAILADDRESS"] is None or u["EMAILADDRESS"].strip() == "": continue
        if user == _("(all)", l) or user == _("(everyone)", l):
            send_email(dbo, fromadd, u["EMAILADDRESS"], "", subject, body)
        elif u["USERNAME"] == user:
            send_email(dbo, fromadd, u["EMAILADDRESS"], "", subject, body)
        elif nulltostr(u["ROLES"]).find(user) != -1:
            send_email(dbo, fromadd, u["EMAILADDRESS"], "", subject, body)

def html_to_pdf(htmldata, baseurl = "", account = ""):
    """
    Converts HTML content to PDF and returns the PDF file data.
    Uses pisa for the conversion.
    """
    try:
        import sx.pisa3 as pisa
    except:
        al.error("trying to convert html to pdf, pisa not found.", "utils.html_to_pdf", None)
        return ""
    # Allow orientation and papersize to be set
    # with directives in the document source - eg: <!-- pdf orientation landscape, pdf papersize letter -->
    orientation = "portrait"
    papersize = "a4"
    if htmldata.find("pdf orientation landscape") != -1: orientation = "landscape"
    if htmldata.find("pdf orientation portrait") != -1: orientation = "portrait"
    if htmldata.find("pdf papersize a5") != -1: papersize = "a5"
    if htmldata.find("pdf papersize a4") != -1: papersize = "a4"
    if htmldata.find("pdf papersize a3") != -1: papersize = "a3"
    if htmldata.find("pdf papersize letter") != -1: papersize = "letter"
    header = """<!DOCTYPE HTML>
    <html>
    <head>
    <style type='text/css'>
    @page {
        size: %s %s;
        margin: 1cm;
    }
    </style>""" % (papersize, orientation)
    header += '<meta http-equiv="content-type" content="text/html; charset=utf-8">\n'
    header += "</head><body>"
    footer = "</body></html>"
    htmldata = htmldata.replace("font-size: xx-small", "font-size: 6pt")
    htmldata = htmldata.replace("font-size: x-small", "font-size: 8pt")
    htmldata = htmldata.replace("font-size: small", "font-size: 10pt")
    htmldata = htmldata.replace("font-size: medium", "font-size: 14pt")
    htmldata = htmldata.replace("font-size: large", "font-size: 18pt")
    htmldata = htmldata.replace("font-size: x-large", "font-size: 24pt")
    htmldata = htmldata.replace("font-size: xx-large", "font-size: 36pt")
    htmldata = fix_relative_document_uris(htmldata, baseurl, account)
    fin = StringIO(header + str(htmldata) + footer)
    fout = StringIO()
    pdf = pisa.CreatePDF(fin, fout)
    if pdf.err:
        al.error("errors found converting html to pdf.", "utils.html_to_pdf", None)
    else:
        return fout.getvalue()

def generate_label_pdf(dbo, locale, records, papersize, units, hpitch, vpitch, width, height, lmargin, tmargin, cols, rows):
    """
    Generates a PDF of labels from the rows given to the measurements provided.
    papersize can be "a4" or "letter"
    units can be "inch" or "cm"
    all units themselves should be floats, cols and rows should be ints
    """
    #from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4, inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    unit = inch
    if units == "cm":
        unit = cm
    psize = A4
    if papersize == "letter":
        psize = letter

    # Not used since they control inner margins within hpitch/vpitch
    dummy = height
    dummy = width

    fout = StringIO()
    doc = SimpleDocTemplate(fout, pagesize=psize, leftMargin = lmargin * unit, topMargin = tmargin * unit, rightMargin = 0, bottomMargin = 0)
    col = 0
    row = 0
    elements = []

    def newData():
        l = []
        for dummy in xrange(0, rows):
            l.append( [ "" ] * cols )
        return l

    def addToData(rd, datad, cold, rowd):
        # Ref: http://bitboost.com/ref/internal-address-formats/
        template = "%(name)s\n%(address)s\n%(postcode)s %(town)s %(county)s"
        if locale in ( "en", "en_CA", "en_AU", "en_IN", "en_KA", "en_PH", "en_TH", "en_VN", "th" ):
            # US style, city/state/zip on last line
            template = "%(name)s\n%(address)s\n%(town)s %(county)s %(postcode)s"
        elif locale in ( "en_GB", "en_IE", "en_ZA" ):
            # UK style, postcode on last line
            template = "%(name)s\n%(address)s\n%(town)s\n%(county)s\n%(postcode)s"
        elif locale in ( "bs", "bg", "cs", "de", "el", "en_CN", "en_NZ", "es", 
            "es_EC", "en_MX", "es_MX", "fr", "he", "it", "lt", "nb", "nl", "pl", "pt", 
            "ru", "sk", "sl", "sv", "tr" ):
            # European style, postcode precedes city/state on last line
            template = "%(name)s\n%(address)s\n%(postcode)s %(town)s %(county)s"
        ad = template % { "name": str(rd["OWNERNAME"]).strip(), "address": rd["OWNERADDRESS"], "town": rd["OWNERTOWN"],
            "county": rd["OWNERCOUNTY"], "postcode": rd["OWNERPOSTCODE"] }
        #al.debug("Adding to data col=%d, row=%d, val=%s" % (cold, rowd, ad))
        datad[rowd][cold] = decode_html(ad)

    def addTable(datad):
        #al.debug("Adding data to table: " + str(datad))
        t = Table(datad, cols * [ hpitch * unit ], rows * [ vpitch * unit ])
        t.hAlign = "LEFT"
        t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
        # If we have more than 8 labels vertically, use a smaller font
        if rows > 8:
            t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                   ("FONTSIZE", (0,0), (-1,-1), 8)]))
        elements.append(t)

    data = newData()
    al.debug("creating mailing label PDF from %d rows" % len(records), "utils.generate_label_pdf", dbo)
    for r in records:
        addToData(r, data, col, row)
        # move to next label position
        col += 1
        if col == cols: 
            row += 1
            col = 0
            if row == rows:
                # We've filled the page, create the table and add it
                row = 0
                col = 0
                addTable(data)
                # reset the data for the next page
                data = newData()
                # TODO: Add pagebreak?

    # Add anything pending to the page
    addTable(data)
    # Build the PDF
    doc.build(elements)
    return fout.getvalue()
