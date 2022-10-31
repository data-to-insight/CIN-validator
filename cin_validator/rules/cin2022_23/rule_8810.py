from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import CINTable, RuleContext, rule_definition
from cin_validator.test_engine import run_rule

# Get tables and columns of interest from the CINTable object defined in rule_engine/__api.py

CINdetails = CINTable.CINdetails
ReasonForClosure = CINdetails.ReasonForClosure
CINclosureDate = CINdetails.CINclosureDate
LAchildID = CINdetails.LAchildID

# define characteristics of rule
@rule_definition(
    # write the rule code here, in place of 8500
    code=8810,
    # replace ChildIdentifiers with the value in the module column of the excel sheet corresponding to this rule .
    module=CINTable.CINdetails,
    # replace the message with the corresponding value for this rule, gotten from the excel sheet.
    message="A CIN case cannot have a Reason for Closure without a CIN Closure Date",
    # The column names tend to be the words within the < > signs in the github issue description.
    affected_fields=[ReasonForClosure, CINclosureDate],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    # PREPARING DATA

    # Replace ChildIdentifiers with the name of the table you need.
    df = data_container[CINdetails]
    # Before you begin, rename the index so that the initial row positions can be kept intact.
    df.index.name = "ROW_ID"

    # lOGIC
    # Implement rule logic as described by the Github issue.
    # Put the description as a comment above the implementation as shown.

    # If <ReasonForClosure> (N00103) is present then <CINclosureDate> (N00102) must also be present
    # Return rows where there is a Reason for closure and no CINclosureDate
    condition = df[ReasonForClosure].notna() & df[CINclosureDate].isna()
    # get all the data that fits the failing condition. Reset the index so that ROW_ID now becomes a column of df
    df_issues = df[condition].reset_index()

    # SUBMIT ERRORS
    # Generate a unique ID for each instance of an error. In this case,
    # - If only LAchildID is used as an identifier, multiple instances of the error on a child will be understood as 1 instance.
    # We don't want that because in reality, a child can have multiple instances of an error.
    # - If we use the LAchildID-CPPstartDate combination, that artificially cancels out the instances where a start date repeats for the same child.
    # Another rule checks for that condition. Not this one.
    # - It is very unlikely that a combination of LAchildID-CPPstartDate-CPPendDate will repeat in the DataFrame.
    # Hence, it can be used as a unique identifier of the row.

    # Replace CPPstartDate and CPPendDate below with the columns concerned in your rule.
    link_id = tuple(
        zip(
            df_issues[LAchildID], df_issues[ReasonForClosure], df_issues[CINclosureDate]
        )
    )
    df_issues["ERROR_ID"] = link_id
    df_issues = df_issues.groupby("ERROR_ID")["ROW_ID"].apply(list).reset_index()
    # Ensure that you do not change the ROW_ID, and ERROR_ID column names which are shown above. They are keywords in this project.
    rule_context.push_type_1(
        table=CINdetails, columns=[ReasonForClosure, CINclosureDate], row_df=df_issues
    )


def test_validate():
    # Create some sample data such that some values pass the validation and some fail.
    fake_data_frame = pd.DataFrame(
        [
            {
                "LAchildID": "child1",
                "ReasonForClosure": "26/05/2000",
                "CINclosureDate": "26/05/2000",
            },
            {
                "LAchildID": "child2",
                "ReasonForClosure": "26/05/2000",
                "CINclosureDate": "26/05/2001",
            },
            {
                "LAchildID": "child3",
                "ReasonForClosure": "26/05/2000",
                "CINclosureDate": pd.NA,
            },  #  Fails because there is a ReasonForClosure and no CINclosureDate
            {
                "LAchildID": "child4",
                "ReasonForClosure": "26/05/2000",
                "CINclosureDate": pd.NA,
            },  #  Fails because there is a ReasonForClosure and no CINclosureDate
            {
                "LAchildID": "child4",
                "ReasonForClosure": pd.NA,
                "CINclosureDate": "25/05/2000",
            },
            {
                "LAchildID": "child5",
                "ReasonForClosure": pd.NA,
                "CINclosureDate": pd.NA,
            },
        ]
    )
    #  Date values not checked so no datetime conversion.

    # Run rule function passing in our sample data
    result = run_rule(validate, {CINdetails: fake_data_frame})

    # Use .type1_issues to check for the result of .push_type1_issues() which you used above.
    issues = result.type1_issues

    # get table name and check it. Replace ChildProtectionPlans with the name of your table.
    issue_table = issues.table
    assert issue_table == CINdetails

    # check that the right columns were returned. Replace CPPstartDate and CPPendDate with a list of your columns.
    issue_columns = issues.columns
    assert issue_columns == [ReasonForClosure, CINclosureDate]

    # check that the location linking dataframe was formed properly.
    issue_rows = issues.row_df
    # replace 2 with the number of failing points you expect from the sample data.
    assert len(issue_rows) == 2
    # check that the failing locations are contained in a DataFrame having the appropriate columns. These lines do not change.
    assert isinstance(issue_rows, pd.DataFrame)
    assert issue_rows.columns.to_list() == ["ERROR_ID", "ROW_ID"]

    # Create the dataframe which you expect, based on the fake data you created. It should have two columns.
    # - The first column is ERROR_ID which contains the unique combination that identifies each error instance, which you decided on earlier.
    # - The second column in ROW_ID which contains a list of index positions that belong to each error instance.

    # The ROW ID values represent the index positions where you expect the sample data to fail the validation check.
    expected_df = pd.DataFrame(
        [
            {
                "ERROR_ID": (
                    "child3",
                    "26/05/2000",
                    pd.NA,
                ),
                "ROW_ID": [2],
            },
            {
                "ERROR_ID": (
                    "child4",
                    "26/05/2000",
                    pd.NA,
                ),
                "ROW_ID": [3],
            },
        ]
    )
    assert issue_rows.equals(expected_df)

    # Check that the rule definition is what you wrote in the context above.

    # replace 8925 with the rule code and put the appropriate message in its place too.
    assert result.definition.code == 8810
    assert (
        result.definition.message
        == "A CIN case cannot have a Reason for Closure without a CIN Closure Date"
    )
