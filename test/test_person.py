#!/usr/bin/python env

import unittest
import base

import person
import utils

class TestPerson(unittest.TestCase):
   
    nid = 0

    def setUp(self):
        data = {
            "title": "Mr",
            "forenames": "Test",
            "surname": "Testing",
            "ownertype": "1",
            "address": "123 test street"
        }
        post = utils.PostedData(data, "en")
        self.nid = person.insert_person_from_form(base.get_dbo(), post, "test")

    def tearDown(self):
        person.delete_person(base.get_dbo(), "test", self.nid)

    def test_get_homechecked(self):
        assert 0 == len(person.get_homechecked(base.get_dbo(), self.nid))

    def test_get_person(self):
        person.get_person(base.get_dbo(), self.nid)

    def test_get_person_similar(self):
        assert len(person.get_person_similar(base.get_dbo(), "Testing", "", "123")) > 0

    def test_get_person_name(self):
        assert "" != person.get_person_name(base.get_dbo(), self.nid)

    def test_get_person_name_code(self):
        assert "" != person.get_person_name_code(base.get_dbo(), self.nid)

    def test_get_towns(self):
        person.get_towns(base.get_dbo())

    def test_get_town_to_county(self):
        person.get_town_to_county(base.get_dbo())

    def test_get_counties(self):
        person.get_counties(base.get_dbo())

    def test_get_satellite_counts(self):
        person.get_satellite_counts(base.get_dbo(), self.nid)

    def test_get_reserves_without_homechecks(self):
        person.get_reserves_without_homechecks(base.get_dbo())

    def test_get_overdue_donations(self):
        person.get_overdue_donations(base.get_dbo())

    def test_get_links(self):
        person.get_links(base.get_dbo(), self.nid)

    def test_get_investigation(self):
        person.get_investigation(base.get_dbo(), self.nid)
       
    def test_get_person_find_simple(self):
        assert len(person.get_person_find_simple(base.get_dbo(), "Test")) > 0

    def test_get_person_find_advanced(self):
        assert len(person.get_person_find_advanced(base.get_dbo(), { "name": "Test" })) > 0

    def test_investigation_crud(self):
        data = {
            "personid": str(self.nid),
            "date": base.today_display(),
            "notes": "Test"
        }
        post = utils.PostedData(data, "en")
        iid = person.insert_investigation_from_form(base.get_dbo(), "test", post)
        data["investigationid"] = str(iid)
        person.update_investigation_from_form(base.get_dbo(), "test", post)
        person.delete_investigation(base.get_dbo(), "test", iid)

    def test_update_pass_homecheck(self):
        person.update_pass_homecheck(base.get_dbo(), "test", self.nid, "")

    def test_update_missing_geocodes(self):
        person.update_missing_geocodes(base.get_dbo())

    def test_update_lookingfor_report(self):
        person.update_lookingfor_report(base.get_dbo())

