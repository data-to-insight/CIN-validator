"""
Rule number: 1105
Module: Child protection plans
Rule details: Where present, the <CPPStartDate> (N00105) must be on or after the <CINReferralDate> (N00100)
Rule message: The child protection plan start date cannot be before the referral date

"""
from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import rule_definition, CINTable, RuleContext
from cin_validator.rule_engine import IssueLocator
from cin_validator.test_engine import run_rule

# Get tables and columns of interest from the CINTable object defined in rule_engine/__api.py

ChildProtectionPlans = CINTable.ChildProtectionPlans
CPPstartDate = ChildProtectionPlans.CPPstartDate
CPP_LAID = ChildProtectionPlans.LAchildID
CPP_CINdetailsID = ChildProtectionPlans.CINdetailsID

CINDetails = CINTable.CINdetails
CINreferralDate = CINDetails.CINreferralDate
CIN_LAID = CINDetails.LAchildID
CIN_CINdetailsID = CINDetails.CINdetailsID

# define characteristics of rule
@rule_definition(
    code=1105,
    module=CINTable.ChildProtectionPlans,
    message="The child protection plan start date cannot be before the referral date",
    affected_fields=[
        CPPstartDate,
        CINreferralDate,
    ],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    df_CPP = data_container[ChildProtectionPlans].copy()
    df_CIN = data_container[CINDetails].copy()

    df_CPP.index.name = "ROW_ID"
    df_CIN.index.name = "ROW_ID"

    df_CPP.reset_index(inplace=True)
    df_CIN.reset_index(inplace=True)

    # Remove rows without CPP start date

    df_CPP = df_CPP[df_CPP[CPPstartDate].notna()]

    # <CPPStartDate> (N00105) must be on or after the <CINReferralDate> (N00100)

    # Join 2 tables together

    df = df_CPP.merge(
        df_CIN,
        left_on=["LAchildID", "CINdetailsID"],
        right_on=["LAchildID", "CINdetailsID"],
        how="left",
        suffixes=("_CPP", "_CIN"),
    )

    # Return those where dates don't align
    df = df[df["CINreferralDate"] > df["CPPstartDate"]].reset_index()

    df["ERROR_ID"] = tuple(zip(df["LAchildID"], df[CPPstartDate], df[CINreferralDate]))

    df_CPP_issues = (
        df_CPP.merge(df, left_on="ROW_ID", right_on="ROW_ID_CIN")
        .groupby("ERROR_ID")["ROW_ID"]
        .apply(list)
        .reset_index()
    )
    print(df_CPP_issues)

    df_CIN_issues = (
        df_CIN.merge(df, left_on="ROW_ID", right_on="ROW_ID_CPP")
        .groupby("ERROR_ID")["ROW_ID"]
        .apply(list)
        .reset_index()
    )

    rule_context.push_type_2(
        table=ChildProtectionPlans, columns=[CPPstartDate], row_df=df_CPP_issues
    )
    rule_context.push_type_2(
        table=CINDetails, columns=[CINreferralDate], row_df=df_CIN_issues
    )


def test_validate():
    # Create some sample data such that some values pass the validation and some fail.
    sample_CPP = pd.DataFrame(
        [
            {
                "LAchildID": "child1",
                "CPPstartDate": "26/05/2000",  # Pass, same date
                "CINdetailsID": "cinID1",
            },
            {
                "LAchildID": "child1",
                "CPPstartDate": "27/06/2002",  # Pass, after referall
                "CINdetailsID": "cinID2",
            },
            {
                "LAchildID": "child3",
                "CPPstartDate": "07/02/1999",  # Fail, prior to referall
                "CINdetailsID": "cinID6",
            },
            {
                "LAchildID": "child2",
                "CPPstartDate": "26/05/2000",  # Fail, prior to referral
                "CINdetailsID": "cinID3",
            },
            {
                "LAchildID": "child3",
                "CPPstartDate": "26/05/2001",  # Pass, after referall
                "CINdetailsID": "cinID4",
            },
        ]
    )

    sample_CIN = pd.DataFrame(
        [
            {
                "LAchildID": "child1",  # Pass
                "CINreferralDate": "26/05/2000",
                "CINdetailsID": "cinID1",
            },
            {
                "LAchildID": "child1",  # Pass
                "CINreferralDate": "26/05/2000",
                "CINdetailsID": "cinID2",
            },
            {
                "LAchildID": "child3",  # Fail
                "CINreferralDate": "26/05/2000",
                "CINdetailsID": "cinID6",
            },
            {
                "LAchildID": "child2",  # Fail
                "CINreferralDate": "30/05/2000",
                "CINdetailsID": "cinID3",
            },
            {
                "LAchildID": "child3",  # Pass
                "CINreferralDate": "27/05/2000",
                "CINdetailsID": "cinID4",
            },
        ]
    )

    sample_CPP[CPPstartDate] = pd.to_datetime(
        sample_CPP[CPPstartDate], format="%d/%m/%Y", errors="coerce"
    )
    sample_CIN[CINreferralDate] = pd.to_datetime(
        sample_CIN[CINreferralDate], format="%d/%m/%Y", errors="coerce"
    )

    # Run rule function passing in our sample data
    result = run_rule(
        validate,
        {
            ChildProtectionPlans: sample_CPP,
            CINDetails: sample_CIN,
        },
    )

    # The result contains a list of issues encountered
    issues_list = result.type2_issues
    assert len(issues_list) == 2

    issues = issues_list[1]

    # get table name and check it. Replace Reviews with the name of your table.
    issue_table = issues.table
    assert issue_table == CINDetails

    # check that the right columns were returned. Replace CPPreviewDate  with a list of your columns.
    issue_columns = issues.columns
    assert issue_columns == [CINreferralDate]

    # check that the location linking dataframe was formed properly.
    issue_rows = issues.row_df
    # replace 3 with the number of failing points you expect from the sample data.
    assert len(issue_rows) == 2
    # check that the failing locations are contained in a DataFrame having the appropriate columns. These lines do not change.
    assert isinstance(issue_rows, pd.DataFrame)
    assert issue_rows.columns.to_list() == ["ERROR_ID", "ROW_ID"]

    expected_df = pd.DataFrame(
        [
            {
                "ERROR_ID": (
                    "child2",  # ChildID
                    # Start date
                    pd.to_datetime("26/05/2000", format="%d/%m/%Y", errors="coerce"),
                    # Referral date
                    pd.to_datetime("30/05/2000", format="%d/%m/%Y", errors="coerce"),
                ),
                "ROW_ID": [3],
            },
            {
                "ERROR_ID": (
                    "child3",  # ChildID
                    # Start Date
                    pd.to_datetime("07/02/1999", format="%d/%m/%Y", errors="coerce"),
                    # Referral date
                    pd.to_datetime("26/05/2000", format="%d/%m/%Y", errors="coerce"),
                ),
                "ROW_ID": [2],
            },
        ]
    )

    assert issue_rows.equals(expected_df)

    assert result.definition.code == 1105
    assert (
        result.definition.message
        == "The child protection plan start date cannot be before the referral date"
    )
