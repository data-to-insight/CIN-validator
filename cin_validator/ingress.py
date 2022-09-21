# TODO Possible tests for this file
# - Check that no generated table has more columns than expected.
# - Check that all generated tables have the required IDs.
# - Check that Header, ChildIdentifiers, and ChildCharacteristics tags do not repeat and have no duplicate subelements.
# - Check that all expected columns are created for every appropriate xml block found.

import pandas as pd
import xml.etree.ElementTree as ET

# TODO make this work with from cin_validator.utils import get_values
from utils import get_values

# initialize all data sets as empty dataframes with columns names
# whenever a child is created, it should add a row to each table where it exists.
# tables should be attributes of a class that are accessible to the methods in create_child.
class XMLtoCSV():
    # define column names from CINTable object.
    Header = pd.DataFrame(columns=["Collection", "Year", "ReferenceDate", "SourceLevel", "LEA", "SoftwareCode", "Release", "SerialNo", "DateTime"])
    ChildIdentifiers = pd.DataFrame(columns=["LAchildID", "UPN", "FormerUPN", "UPNunknown", "PersonBirthDate", "ExpectedPersonBirthDate", "GenderCurrent", "PersonDeathDate"])
    ChildCharacteristics = pd.DataFrame(columns=["LAchildID", "Ethnicity", ])
    Disabilities = pd.DataFrame(columns=["LAchildID", "Disability"])
    CINdetails = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "CINreferralDate", "ReferralSource", "PrimaryNeedCode", "CINclosureDate", "ReasonForClosure", "DateOfInitialCPC", "ReferralNFA" ])
    Assessments = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "AssessmentActualStartDate", "AssessmentInternalReviewDate", "AssessmentAuthorisationDate", "AssessmentFactors"]) 
    CINplanDates = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "CINPlanStartDate", "CINPlanEndDate"])
    Section47 = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "S47ActualStartDate", "InitialCPCtarget", "DateOfInitialCPC", "ICPCnotRequired"])
    ChildProtectionPlans = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "CPPID", "CPPstartDate", "CPPendDate", "InitialCategoryOfAbuse", "LatestCategoryOfAbuse", "NumberOfPreviousCPP"]) 
    Reviews = pd.DataFrame(columns=["LAchildID", "CINdetailsID", "CPPID", "CPPreviewDate"])

    id_cols = ["LAchildID", "CINdetailsID", "CPPID"]

    def __init__(self, root):
        header = root.find("Header")
        self.Header = self.create_Header(header)

        children = root.find("Children")
        for child in children.findall('Child'):
            self.create_child(child)

# for each table, column names should attempt to find their value in the child.
# if not found, they should assign themselves to NaN

    def create_child(self, child):
        # at the start of every child, reset the value of LAchildID
        self.LAchildID = None

        self.create_ChildIdentifiers(child)
        # LAchildID has been created. It can be used in the functions below.
        self.create_ChildCharacteristics(child)
        
        # CINdetailsID needed
        self.create_CINdetails(child)
        
        # CINdetails and CPPID needed
        self.create_ChildProtectionPlans(child)
        self.create_Reviews(child)

    # TODO get column names from the CINTable object instead of writing them out as strings?
    def create_Header(self, header):
        """One header exists in a CIN XML file"""

        header_dict = {}

        collection_details = header.find('CollectionDetails')
        collection_elements = ['Collection', 'Year', 'ReferenceDate']
        header_dict = get_values(collection_elements, header_dict, collection_details)

        source = header.find('Source')
        source_elements = ['SourceLevel', 'LEA', 'SoftwareCode', 'Release', 'SerialNo', 'DateTime']
        header_dict = get_values(source_elements, header_dict, source)

        header_df = pd.DataFrame.from_dict([header_dict])
        return header_df

    def create_ChildIdentifiers(self, child):
        """One ChildIdentifiers block exists per child in CIN XML"""
        # pick out the values of relevant columns
        # add to the global attribute
        identifiers_dict = {}

        identifiers = child.find('ChildIdentifiers')
        elements = self.ChildIdentifiers.columns
        identifiers_dict = get_values(elements, identifiers_dict, identifiers)
        
        self.LAchildID = identifiers_dict.get('LAchildID', pd.NA)

        identifiers_df = pd.DataFrame.from_dict([identifiers_dict])
        self.ChildIdentifiers = pd.concat([self.ChildIdentifiers, identifiers_df], ignore_index=True)

    def create_ChildCharacteristics(self, child):
        """One ChildCharacteristics block exists per child in CIN XML"""
        # assign LAChild ID
        characteristics_dict = {'LAchildID':self.LAchildID}

        characteristics = child.find('ChildCharacteristics')
        columns = self.ChildCharacteristics.columns
        # select only columns whose values typically exist in this xml block.
        # remove id_cols which tend to come from other blocks or get generated at runtime.
        elements = list(set(columns).difference(set(self.id_cols)))

        characteristics_dict = get_values(elements, characteristics_dict, characteristics)

        characteristics_df = pd.DataFrame.from_dict([characteristics_dict])
        self.ChildCharacteristics = pd.concat([self.ChildCharacteristics, characteristics_df], ignore_index=True)

    # CINdetailsID needed
    def create_CINdetails(self, child):
        """Multiple CIN details blocks can exist in one child."""

        cin_details_list = []
        columns = self.CINdetails.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        # imitate DfE generator where the ID count for the first child is 1
        self.CINdetailsID = 0

        cin_details = child.findall('CINdetails')
        for cin_detail in cin_details:
            self.CINdetailsID += 1
            cin_detail_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID}

            cin_detail_dict = get_values(elements, cin_detail_dict, cin_detail)
            cin_details_list.append(cin_detail_dict)

            # functions that should use the CINdetailsID before it is incremented.
            self.create_Assessments(cin_detail)
            self.create_CINplanDates(cin_detail)
            self.create_Section47(cin_detail)
            self.create_ChildProtectionPlans(cin_detail)
        
        cin_details_df = pd.DataFrame(cin_details_list)
        self.CINdetails = pd.concat([self.CINdetails, cin_details_df], ignore_index=True)

        
    def create_Assessments(self, cin_detail):
        """Multiple Assessments blocks can exist in one CINdetails block."""

        assessments_list = []
        columns = self.Assessments.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        assessments = cin_detail.findall('Assessments')
        for assessment in assessments:
            # all the assessment descriptors repeat to create a row for each assessment factor.
            assessment_factors = assessment.find('FactorsIdentifiedAtAssessment')
            for factor in assessment_factors:
                assessment_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID,}
                assessment_dict = get_values(elements, assessment_dict, assessment)
                # the get_values function will not find AssessmentFactors on that level so it'll assign it to NaN
                assessment_dict['AssessmentFactors'] = factor.text
                assessments_list.append(assessment_dict)
        
        assessments_df = pd.DataFrame(assessments_list)
        self.Assessments = pd.concat([self.Assessments, assessments_df], ignore_index=True)

    def create_CINplanDates(self, cin_detail):
        """Multiple CINplanDates blocks can exist in one CINdetails block."""

        dates_list = []
        columns = self.CINplanDates.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        dates = cin_detail.findall('CINPlanDates')
        for date in dates:
            date_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID,}
            date_dict = get_values(elements, date_dict, date)
            dates_list.append(date_dict)
        
        dates_df = pd.DataFrame(dates_list)
        self.CINplanDates = pd.concat([self.CINplanDates, dates_df], ignore_index=True)
        
    def create_Section47(self, cin_detail):
        """Multiple Section47 blocks can exist in one CINdetails block."""

        sections_list = []
        columns = self.Section47.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        sections = cin_detail.findall('Section47')
        for section in sections:
            section_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID,}
            section_dict = get_values(elements, section_dict, section)
            sections_list.append(section_dict)
        
        sections_df = pd.DataFrame(sections_list)
        self.Section47 = pd.concat([self.Section47, sections_df], ignore_index=True)
        
    # CINdetails and CPPID needed
    def create_ChildProtectionPlans(self, cin_detail):
        """Multiple ChildProtectionPlans blocks can exist in one CINdetails block."""

        plans_list = []
        columns = self.ChildProtectionPlans.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        # imitate DfE generator where the first counted thing starts from 1.
        self.CPPID = 0

        plans = cin_detail.findall('ChildProtectionPlans')
        for plan in plans:
            self.CPPID += 1
            plan_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID, 'CPPID' : self.CPPID}
            plan_dict = get_values(elements, plan_dict, plan)
            plans_list.append(plan_dict)

            # functions that should use CPPID before it is incremented
            self.create_Reviews(plan)
        
        plans_df = pd.DataFrame(plans_list)
        self.ChildProtectionPlans = pd.concat([self.ChildProtectionPlans, plans_df], ignore_index=True)
        
    def create_Reviews(self, plan):
        """Multiple Reviews blocks can exist in one ChildProtectionPlans block."""

        reviews_list = []
        columns = self.Reviews.columns
        elements = list(set(columns).difference(set(self.id_cols)))

        reviews = plan.findall('Reviews')
        for review in reviews:
            review_dict = {'LAchildID':self.LAchildID, 'CINdetailsID': self.CINdetailsID, 'CPPID' : self.CPPID}
            review_dict = get_values(elements, review_dict, review)

            reviews_list.append(review_dict)

        reviews_df = pd.DataFrame(reviews_list)
        self.Reviews = pd.concat([self.Reviews, reviews_df], ignore_index=True)


# TODO make file path os-independent
fulltree = ET.parse("../fake_data/CIN_Census_2021.xml")
# fulltree = ET.parse("../fake_data/fake_CIN_data.xml")

message = fulltree.getroot()

conv = XMLtoCSV(message)
print(conv.Reviews)

"""
Sidenote: Fields absent from the fake_CIN_data.xml
- Assessments
- CINPlanDates
- Section47
- ChildProtectionPlans
- Reviews
"""