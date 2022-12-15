from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import CINTable, RuleContext, rule_definition
from cin_validator.test_engine import run_rule
from cin_validator.utils import make_census_period

# Get tables and columns of interest from the CINTable object defined in rule_engine/__api.py

ChildIdentifiers = CINTable.ChildIdentifiers
CINdetails = CINTable.CINdetails

LAchildID = ChildIdentifiers.LAchildID

# define characteristics of rule
@rule_definition(
    # write the rule code here, in place of 2885
    code=8590,
    # replace ChildProtectionPlans with the value in the module column of the excel sheet corresponding to this rule .
    # Note that even if multiple tables are involved, one table will be named in the module column.
    module=CINTable.ChildIdentifiers,
    # replace the message with the corresponding value for this rule, gotten from the excel sheet.
    message="Child does not have a recorded CIN episode.",
    # The column names tend to be the words within the < > signs in the github issue description.
    affected_fields=[LAchildID],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    # PREPARING DATA

    # Replace ChildProtectionPlans with the name of the table you need.
    df_cid = data_container[ChildIdentifiers].copy()
    df_cin = data_container[CINdetails].copy()

    # Before you begin, rename the index so that the initial row positions can be kept intact.
    df_cid.index.name = "ROW_ID"
    df_cin.index.name = "ROW_ID"

    # Resetting the index causes the ROW_IDs to become columns of their respective DataFrames
    # so that they can come along when the merge is done.
    df_cid.reset_index(inplace=True)
    df_cin.reset_index(inplace=True)

    # lOGIC
    # Implement rule logic as described by the Github issue.
    # Put the description as a comment above the implementation as shown.

    # Each child must have at least one <CINdetails> group

    df_merge = df_cid.merge(
        df_cin[LAchildID], on=[LAchildID], how="left", indicator=True
    )
    # get only ChildIdentifiers that don't have a matching CINdetails.
    condition = df_merge["_merge"] == "left_only"

    # get all the data that fits the failing condition.
    df_merge = df_merge[condition].reset_index()

    # create an identifier for each error instance.
    df_merge["ERROR_ID"] = tuple(zip(df_merge[LAchildID]))

    # The merges were done on copies of df_cid etc so that the column names in dataframes themselves aren't affected by the suffixes.
    # we can now map the suffixes columns to their corresponding source tables such that the failing ROW_IDs and ERROR_IDs exist per table.
    df_cid_issues = (
        df_cid.merge(df_merge, left_on="ROW_ID", right_on="ROW_ID")
        .groupby("ERROR_ID", group_keys=False)["ROW_ID"]
        .apply(list)
        .reset_index()
    )

    # Ensure that you maintain the ROW_ID, and ERROR_ID column names which are shown above. They are keywords in this project.
    rule_context.push_type_2(
        table=ChildIdentifiers, columns=[LAchildID], row_df=df_cid_issues
    )


def test_validate():
    # Create some sample data such that some values pass the validation and some fail.
    sample_child_identifiers = pd.DataFrame(
        [
            {
                "LAchildID": "child1",  # Pass
            },
            {
                "LAchildID": "child2",  # Pass
            },
            {
                "LAchildID": "child3",  # Fail
            },
            {
                "LAchildID": "child4",  # Pass
            },
        ]
    )
    sample_cin_details = pd.DataFrame(
        [
            {
                "LAchildID": "child1",  # Pass
            },
            {
                "LAchildID": "child2",  # Pass
            },
            {
                "LAchildID": "child4",  # Pass
            },
            {
                "LAchildID": "child5",  # Ignore
            },
        ]
    )

    # Run the rule function, passing in our sample data.
    result = run_rule(
        validate,
        {
            ChildIdentifiers: sample_child_identifiers,
            CINdetails: sample_cin_details,
        },
    )

    # Use .type2_issues to check for the result of .push_type2_issues() which you used above.
    issues_list = result.type2_issues
    assert len(issues_list) == 1
    # the function returns a list on NamedTuples where each NamedTuple contains (table, column_list, df_issues)
    # pick any table and check it's values. the tuple in location 1 will contain the Section47 columns because that's the second thing pushed above.
    issues = issues_list[0]

    # get table name and check it. Replace Section47 with the name of your table.
    issue_table = issues.table
    assert issue_table == ChildIdentifiers

    # check that the right columns were returned. Replace DateOfInitialCPC  with a list of your columns.
    issue_columns = issues.columns
    assert issue_columns == [LAchildID]

    # check that the location linking dataframe was formed properly.
    issue_rows = issues.row_df
    # replace 2 with the number of failing points you expect from the sample data.
    assert len(issue_rows) == 1
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
                "ERROR_ID": ("child3",),  # ChildID
                "ROW_ID": [2],
            },
        ]
    )
    assert issue_rows.equals(expected_df)

    # Check that the rule definition is what you wrote in the context above.

    # replace 2885 with the rule code and put the appropriate message in its place too.
    assert result.definition.code == 8590
    assert result.definition.message == "Child does not have a recorded CIN episode."