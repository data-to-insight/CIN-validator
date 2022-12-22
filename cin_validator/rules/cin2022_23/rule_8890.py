from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import CINTable, RuleContext, rule_definition
from cin_validator.test_engine import run_rule
from cin_validator.utils import make_census_period

# Get tables and columns of interest from the CINTable object defined in rule_engine/__api.py

Section47 = CINTable.Section47
LAchildID = Section47.LAchildID
CINdetailsID = Section47.CINdetailsID
DateOfInitialCPC = Section47.DateOfInitialCPC
S47ActualStartDate = Section47.S47ActualStartDate
ICPCnotRequired = Section47.ICPCnotRequired

Header = CINTable.Header
ReferenceDate = Header.ReferenceDate

# define characteristics of rule
@rule_definition(
    # write the rule code here
    code=8890,
    # replace CINdetails with the value in the module column of the excel sheet corresponding to this rule .
    # Note that even if multiple tables are involved, one table will be named in the module column.
    module=CINTable.CINdetails,
    # replace the message with the corresponding value for this rule, gotten from the excel sheet.
    message="A Section 47 enquiry is shown as starting when there is another Section 47 Enquiry ongoing",
    # The column names tend to be the words within the < > signs in the github issue description.
    affected_fields=[
        S47ActualStartDate,
    ],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    # PREPARING DATA

    # Replace ChildProtectionPlans with the name of the table you need.
    df_47 = data_container[Section47].copy()
    df_47_2 = data_container[Section47].copy()

    # Before you begin, rename the index so that the initial row positions can be kept intact.
    df_47.index.name = "ROW_ID"
    df_47_2.index.name = "ROW_ID"

    # Resetting the index causes the ROW_IDs to become columns of their respective DataFrames
    # so that they can come along when the merge is done.
    df_47.reset_index(inplace=True)
    df_47_2.reset_index(inplace=True)

    # ReferenceDate exists in the header table so we get header table too.
    df_ref = data_container[Header]
    ref_date_series = df_ref[ReferenceDate]

    # the make_census_period function generates the start and end date so that you don't have to do it each time.
    collection_start, reference_date = make_census_period(ref_date_series)

    # lOGIC
    # Implement rule logic as described by the Github issue.
    # Put the description as a comment above the implementation as shown.

    # Within one <CINdetails> group, each <S47ActualStartDate> (N00148) must not fall on or between
    # a) the <S47ActualStartDate> (N00148) and <DateOfInitialCPC> (N00110) of any other <Section47> group that has a <DateOfInitialCPC> (N00110) or
    # b) the <S47ActualStartDate> (N00148) and the <ReferenceDate> (N00603) of any other <Section47> group
    #   that has a missing <DateOfInitialCPC> (N00110) and the <ICPCnotRequired> (N00111) flag is not true

    #  Create dataframes which only have rows with CP plans, and which should have one plan per row.
    df_47 = df_47[df_47[S47ActualStartDate].notna()]
    df_47_2 = df_47_2[df_47_2[S47ActualStartDate].notna()]

    #  Merge tables to test for overlaps
    df_merged = df_47.merge(
        df_47_2,
        on=[LAchildID, CINdetailsID],
        how="left",
        suffixes=("_47", "_472"),
    )

    # Exclude rows where the CPPID is the same on both sides
    same_start = (
        df_merged["S47ActualStartDate_47"] == df_merged["S47ActualStartDate_472"]
    )
    same_cpc = (
        df_merged["DateOfInitialCPC_47"] == df_merged["DateOfInitialCPC_472"]
    ) | (
        df_merged["DateOfInitialCPC_47"].isna()
        & df_merged["DateOfInitialCPC_472"].isna()
    )
    duplicate = same_start & same_cpc
    df_merged = df_merged[~duplicate]

    # Determine whether CPP overlaps another CPP
    s47_started_after_start = (
        df_merged["S47ActualStartDate_47"] >= df_merged["S47ActualStartDate_472"]
    )
    s47_started_before_end = (
        df_merged["S47ActualStartDate_47"] <= df_merged["DateOfInitialCPC_472"]
    ) & df_merged["DateOfInitialCPC_472"].notna()
    s47_started_before_refdate = (
        (df_merged["S47ActualStartDate_47"] <= reference_date)
        & df_merged["DateOfInitialCPC_472"].isna()
        & (df_merged["ICPCnotRequired_472"] != "1")
    )

    df_merged = df_merged[
        s47_started_after_start & (s47_started_before_end | s47_started_before_refdate)
    ].reset_index()

    # create an identifier for each error instance.
    # In this case, the rule is checked for each CPPstartDate, in each CPplanDates group (differentiated by CP dates), in each child (differentiated by LAchildID)
    df_merged["ERROR_ID"] = tuple(
        zip(
            df_merged[LAchildID],
            df_merged[CINdetailsID],
            df_merged["S47ActualStartDate_47"],
        )
    )

    # The merges were done on copies of cpp_df so that the column names in dataframes themselves aren't affected by the suffixes.
    # we can now map the suffixes columns to their corresponding source tables such that the failing ROW_IDs and ERROR_IDs exist per table.
    df_47_issues = (
        df_47.merge(df_merged, left_on="ROW_ID", right_on="ROW_ID_47")
        .groupby("ERROR_ID", group_keys=False)["ROW_ID"]
        .apply(list)
        .reset_index()
    )

    df_47_2_issues = (
        df_47_2.merge(df_merged, left_on="ROW_ID", right_on="ROW_ID_472")
        .groupby("ERROR_ID", group_keys=False)["ROW_ID"]
        .apply(list)
        .reset_index()
    )

    # Ensure that you maintain the ROW_ID, and ERROR_ID column names which are shown above. They are keywords in this project.
    rule_context.push_type_3(
        table=Section47, columns=[S47ActualStartDate], row_df=df_47_issues
    )
    rule_context.push_type_3(
        table=Section47,
        columns=[S47ActualStartDate, DateOfInitialCPC],
        row_df=df_47_2_issues,
    )


def test_validate():
    # Create some sample data such that some values pass the validation and some fail.
    sample_header = pd.DataFrame(
        [{ReferenceDate: "31/03/2001"}]  # the census start date here will be 01/04/2000
    )

    sample_s47 = pd.DataFrame(
        [  # child1
            {
                "LAchildID": "child1",
                "CINdetailsID": "cinID1",
                "S47ActualStartDate": "26/05/2000",  # 0 Pass: not between "26/08/2000" and "31/03/2001"
                "DateOfInitialCPC": "26/10/2000",
                "ICPCnotRequired": "1",
            },
            {
                "LAchildID": "child1",
                "CINdetailsID": "cinID1",
                "S47ActualStartDate": "26/08/2000",  # 1 Fail: between "26/05/2000" and "26/10/2000"
                "DateOfInitialCPC": pd.NA,
                "ICPCnotRequired": "nottrue",
            },
            {
                "LAchildID": "child2",  # 2 alone in cin group: not compared
                "CINdetailsID": "cinID2",
                "S47ActualStartDate": "26/05/2000",
                "DateOfInitialCPC": "25/10/2000",
                "ICPCnotRequired": "1",
            },
            {
                "LAchildID": "child2",  # 3 alone in cin group: not compared
                "CINdetailsID": "cinID22",
                "S47ActualStartDate": "26/10/2000",
                "DateOfInitialCPC": "26/12/2000",
                "ICPCnotRequired": "1",
            },
            # child3
            {
                "LAchildID": "child3",
                "CINdetailsID": "cinID3",
                "S47ActualStartDate": "26/05/2000",  # 4 Pass: not between "26/08/2000" and "26/10/2000"
                "DateOfInitialCPC": "26/10/2001",
                "ICPCnotRequired": "1",
            },
            {
                "LAchildID": "child3",
                "CINdetailsID": "cinID3",
                "S47ActualStartDate": "26/08/2000",  # 5 Fail: between "26/05/2000" and "26/10/2001"
                "DateOfInitialCPC": "26/10/2000",
                "ICPCnotRequired": "1",
            },
            # child4
            {
                "LAchildID": "child4",
                "CINdetailsID": "cinID1",
                "S47ActualStartDate": "26/10/2000",  # 6 Ignore: between "26/09/2000" and ReferenceDate but ICPCnotRequired is true
                "DateOfInitialCPC": "31/03/2001",
                "ICPCnotRequired": "1",
            },
            {
                "LAchildID": "child4",
                "CINdetailsID": "cinID1",
                "S47ActualStartDate": "26/09/2000",  # 7 Pass: not between "26/10/2000" and "31/03/2001"
                "DateOfInitialCPC": pd.NA,
                "ICPCnotRequired": "1",
            },
        ]
    )

    # If rule requires columns containing date values, convert those columns to datetime objects first. Do it here in the test_validate function, not above.
    sample_s47[S47ActualStartDate] = pd.to_datetime(
        sample_s47[S47ActualStartDate], format="%d/%m/%Y", errors="coerce"
    )
    sample_s47[DateOfInitialCPC] = pd.to_datetime(
        sample_s47[DateOfInitialCPC], format="%d/%m/%Y", errors="coerce"
    )
    sample_header[ReferenceDate] = pd.to_datetime(
        sample_header[ReferenceDate], format="%d/%m/%Y", errors="coerce"
    )

    # Run the rule function, passing in our sample data.
    result = run_rule(
        validate,
        {
            Section47: sample_s47,
            Header: sample_header,
        },
    )

    # Use .type2_issues to check for the result of .push_type2_issues() which you used above.
    issues_list = result.type3_issues
    assert len(issues_list) == 2
    # the function returns a list on NamedTuples where each NamedTuple contains (table, column_list, df_issues)
    # pick any table and check it's values. the tuple in location 1 will contain the Reviews columns because that's the second thing pushed above.
    issues = issues_list[0]

    # get table name and check it. Replace Reviews with the name of your table.
    issue_table = issues.table
    assert issue_table == Section47

    # check that the right columns were returned. Replace CPPreviewDate  with a list of your columns.
    issue_columns = issues.columns
    assert issue_columns == [S47ActualStartDate]

    # check that the location linking dataframe was formed properly.
    issue_rows = issues.row_df
    # replace 3 with the number of failing points you expect from the sample data.
    assert len(issue_rows) == 2

    # check that the failing locations are contained in a DataFrame having the appropriate columns. These lines do not change.
    assert isinstance(issue_rows, pd.DataFrame)
    assert issue_rows.columns.to_list() == ["ERROR_ID", "ROW_ID"]

    # Create the dataframe which you expect, based on the fake data you created. It should have two columns.
    # - The first column is ERROR_ID which contains the unique combination that identifies each error instance, which you decided on, in your zip, earlier.
    # - The second column in ROW_ID which contains a list of index positions that belong to each error instance.

    # The ROW ID values represent the index positions where you expect the sample data to fail the validation check.
    expected_df = pd.DataFrame(
        [
            {
                "ERROR_ID": (
                    "child1",
                    "cinID1",
                    pd.to_datetime("26/08/2000", format="%d/%m/%Y", errors="coerce"),
                ),
                "ROW_ID": [1],
            },
            {
                "ERROR_ID": (
                    "child3",
                    "cinID3",
                    pd.to_datetime("26/08/2000", format="%d/%m/%Y", errors="coerce"),
                ),
                "ROW_ID": [5],
            },
        ]
    )
    assert issue_rows.equals(expected_df)

    # Check that the rule definition is what you wrote in the context above.

    # replace 2885 with the rule code and put the appropriate message in its place too.
    assert result.definition.code == 8890
    assert (
        result.definition.message
        == "A Section 47 enquiry is shown as starting when there is another Section 47 Enquiry ongoing"
    )