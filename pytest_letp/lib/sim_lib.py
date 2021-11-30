"""Manage Carrier, APN, PDP, Band for the sim.

We store an DB in json format, look up its full information for testing.
"""
import collections
import os

from lxml import etree

from pytest_letp.lib import swilog
from pytest_letp.pytest_test_config import TestConfig

__copyright__ = "Copyright (C) Sierra Wireless Inc."


LETP_TESTS = os.environ["LETP_TESTS"]
SIM_CONFIG_PATH = os.path.join(LETP_TESTS, "config/uicc/simdb.xml")


def get_sim_info(target):
    """Use ICCID and IMSI to retrieve correct information.

    Retrieves Carrier, APN, PDP, Band.
    """
    iccid = target.sim_iccid
    imsi = target.sim_imsi
    sim_db = SimDBParser()
    sim_info = sim_db.parse_sim_info(iccid, imsi)
    return sim_info


def validate(element, iccid, imsi):
    """Validate ICCID and IMSI match the prefix in simdb.

    Description:
    Checks if element's ICCID/IMSI is in device's ICCID/IMSI

    :param element: Sim Element containing APN, PDP, Band, ICCIDs, IMSIs
    :param iccid: String containing value of current Device's ICCID
    :param imsi: String containing value of current Device's IMSI

    @Return True if element contains ICCID and IMSI
        False otherwise
    """
    iccid_list = element.find("ICCID_prefix").text.split(",")
    for curr_iccid in iccid_list:
        if curr_iccid in iccid:
            break
    else:
        return False

    # only check if imsi not None
    if imsi:
        imsi_list = element.find("IMSI_prefixes").text.split(",")
        for curr_imsi in imsi_list:
            if curr_imsi in imsi:
                break
        else:
            return False
    return True


class SimDBParser:
    """Class for parsing sibdb.xml."""

    def __init__(self, xmlfile=SIM_CONFIG_PATH):
        """Parse simdb.xml."""
        tree = etree.parse(xmlfile)
        self.root = tree.getroot()
        self.sim_capability_xml_file_name = "simdb"

    def _get_sim_info_path_in_xml(self, sim_type):
        """Get the SIM info XML path in sim capability xml file."""
        return os.path.join(self.sim_capability_xml_file_name, "Operator", sim_type)

    @staticmethod
    def _get_sim_info_detail(element, path):
        """Get text from path in element."""
        try:
            return element.find(path).text
        except AttributeError:
            return None

    def _get_sim_detail(self, sim_type, detail):
        """Get the SIM detail in sim capability xml file."""
        info_path = self._get_sim_info_path_in_xml(sim_type)
        detail_path_in_xml = os.path.join(info_path, detail)
        return self.root.findtext(detail_path_in_xml)

    def get_sim_apn(self, sim_type="Telus"):
        """Get the SIM APN in sim capability xml file."""
        return self._get_sim_detail(sim_type, "APN")

    def get_sim_apn_tcp(self, sim_type="Telus"):
        """Get the SIM APN_TCP in sim capability xml file."""
        return self._get_sim_detail(sim_type, "APN_TCP")

    def get_sim_pdp(self, sim_type="Telus"):
        """Get the SIM PDP in sim capability xml file."""
        return self._get_sim_detail(sim_type, "PDP")

    def get_rf_band(self, sim_type="Telus"):
        """Get the SIM RF band in sim capability xml file."""
        return self._get_sim_detail(sim_type, "Band")

    @staticmethod
    def get_sim_carrier(sim_element):
        """Get the SIM carrier in sim capability xml file."""
        site = TestConfig.default_cfg.get_site()
        carrier = sim_element.tag
        if "Amarisoft" in carrier:
            if site is not None:
                carrier = "Amarisoft_" + site
        return carrier

    def parse_sim_info(self, iccid, imsi):
        """Parse and set Sim information based on ICCID and IMSI.

        :param iccid: Current device's ICCID as a non-empty string
        :param imsi: Current device's IMSI as a non-empty string
        @Returns SimInfo object with updated Carrier,APN,PDP,Band if successful.
            None otherwise
        """
        # Check parameters
        if iccid is None or not isinstance(iccid, str) or iccid == "":
            swilog.warning("No ICCID from current device")
            return None
        elif imsi is None or not isinstance(imsi, str) or imsi == "":
            swilog.warning("No IMSI from current device")
            return None

        is_detail_info = False

        sim_info = []
        apn = None
        # get detail sim info
        for uicc in self.root.findall("simdb/uicc"):
            curr_iccid = uicc.find("iccid").text

            # found iccid
            if curr_iccid in iccid:
                is_detail_info = True
                apn = self._get_sim_info_detail(uicc, "apn")
                sim_info.append(self._get_sim_info_detail(uicc, "iccid"))
                sim_info.append(self._get_sim_info_detail(uicc, "imsi"))
                sim_info.append(self._get_sim_info_detail(uicc, "mcc"))
                sim_info.append(self._get_sim_info_detail(uicc, "mnc"))
                sim_info.append(self._get_sim_info_detail(uicc, "tel"))
                sim_info.append(self._get_sim_info_detail(uicc, "pin"))
                sim_info.append(self._get_sim_info_detail(uicc, "puk"))
                sim_info.append(self._get_sim_info_detail(uicc, "smsc"))
                break

        sim_tuple = []
        sim_elements = self.root.find("simdb/Operator")
        for element in sim_elements:
            if validate(element, iccid, imsi):
                carrier = self.get_sim_carrier(element)
                if apn is None:
                    apn = self.get_sim_apn(sim_type=carrier)
                apn_tcp = self.get_sim_apn_tcp(sim_type=carrier)
                pdp = self.get_sim_pdp(sim_type=carrier)
                band = self.get_rf_band(sim_type=carrier)
                sim_tuple = [carrier, apn, apn_tcp, pdp, band]
                break
        else:
            swilog.warning("Unable to parse Sim Information")
            return None
        sim_tuple.extend(sim_info if is_detail_info else [None] * 8)
        return SimInfo._make(sim_tuple)


class SimInfo(
    collections.namedtuple(
        "SimInfo", "Carrier,APN,APN_TCP,PDP,Band,Iccid,Imsi,Mcc,Mnc,Tel,Pin,Puk,Smsc"
    )
):
    """Class for Sim Information."""
