#!/usr/bin/python

"""
    Geocoding module. Supports google and nominatim
"""

import al
import cachemem
import json
import threading
import time
import utils
from lookups import LOCALE_COUNTRY_NAME_MAP
from sitedefs import BULK_GEO_PROVIDER, BULK_GEO_NOMINATIM_URL, BULK_GEO_GOOGLE_URL, BULK_GEO_LOOKUP_TIMEOUT, BULK_GEO_SLEEP_AFTER

lat_long_lock = threading.Lock()

def get_lat_long(dbo, address, town, county, postcode, country = None):
    """
    Looks up a latitude and longitude from an address using GEOCODE_URL
    and returns them as lat,long,(first 3 chars of address)
    Returns None if no results were found.
    NB: dbo is only used for contextual reference in logging, no database
        calls are made by any of this code.
    """

    if address.strip() == "":
        return None

    try:
        # Synchronise this process to a single thread to prevent
        # abusing our geo provider and concurrent requests for the
        # same address when opening an animal with the same
        # original/brought in by owner, etc.
        lat_long_lock.acquire()

        url = ""
        if country is None: 
            country = LOCALE_COUNTRY_NAME_MAP[dbo.locale]
        if BULK_GEO_PROVIDER == "nominatim":
            q = normalise_nominatim(address, town, county, postcode, country)
            url = BULK_GEO_NOMINATIM_URL.replace("{q}", q)
        elif BULK_GEO_PROVIDER == "google":
            q = normalise_google(address, town, county, postcode, country)
            url = BULK_GEO_GOOGLE_URL.replace("{q}", q)
        else:
            al.error("unrecognised geo provider: %s" % BULK_GEO_PROVIDER, "geo.get_lat_long", dbo)

        al.debug("looking up geocode for address: %s" % q, "geo.get_lat_long", dbo)
        
        key = "nom:" + q
        v = cachemem.get(key)
        if v is not None:
            al.debug("cache hit for address: %s = %s" % (q, v), "geo.get_lat_long", dbo)
            return v

        jr = utils.get_url(url, timeout = BULK_GEO_LOOKUP_TIMEOUT)["response"]
        j = json.loads(jr)

        latlon = None
        if BULK_GEO_PROVIDER == "nominatim":
            latlon = parse_nominatim(dbo, jr, j, q)
        elif BULK_GEO_PROVIDER == "google":
            latlon = parse_google(dbo, jr, j, q)

        if BULK_GEO_SLEEP_AFTER > 0:
            time.sleep(BULK_GEO_SLEEP_AFTER)

        cachemem.put(key, latlon, 86400)
        return latlon

    except Exception,err:
        al.error(str(err), "geo.get_lat_long", dbo)
        return None

    finally:
        lat_long_lock.release()

def parse_nominatim(dbo, jr, j, q):
    if len(j) == 0:
        al.debug("no response from nominatim for %s (response %s)" % (q, str(jr)), "geo.parse_nominatim", dbo)
        return None
    try:
        latlon = "%s,%s,%s" % (str(utils.strip_non_ascii(j[0]["lat"])), str(utils.strip_non_ascii(j[0]["lon"])), "na")
        al.debug("contacted nominatim to get geocode for %s = %s" % (q, latlon), "geo.parse_nominatim", dbo)
        return latlon
    except Exception,err:
        al.error("couldn't find geocode in nominatim response: %s, %s" % (str(err), jr), "geo.parse_nominatim", dbo)
        return None
    
def parse_google(dbo, jr, j, q):
    if len(j) == 0:
        al.debug("no response from google for %s (response %s)" % (q, str(jr)), "geo.parse_google", dbo)
        return None
    try:
        loc = j["results"][0]["geometry"]["location"]
        latlon = "%s,%s,%s" % (str(loc["lat"]), str(loc["lng"]), "na")
        al.debug("contacted google to get geocode for %s = %s" % (q, latlon), "geo.parse_google", dbo)
        return latlon
    except Exception,err:
        al.error("couldn't find geocode in google response. Status was %s: %s, %s" % (j["status"], str(err), jr), "geo.parse_google", dbo)
        return None

def normalise_nominatim(address, town, county, postcode, country):
    q = address + "," + town + "," + country
    q = utils.html_to_uri(q)
    q = q.replace("&", "").replace("=", "").replace("^", "").replace(".", "")
    q = q.replace("\r", "").replace("\n", ",").replace(", ", ",").replace(" ", "+")
    q = q.lower()
    dummy = county + postcode
    return q

def normalise_google(address, town, county, postcode, country):
    q = address + "," + town + "," + county +"," + postcode + "," + country
    q = utils.html_to_uri(q)
    q = q.replace("&", "").replace("=", "").replace("^", "").replace(".", "")
    q = q.replace("\r", "").replace("\n", ",").replace(", ", ",").replace(" ", "+")
    q = q.lower()
    return q


