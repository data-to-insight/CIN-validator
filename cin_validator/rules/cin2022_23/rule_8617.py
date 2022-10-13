from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import rule_definition, CINTable, RuleContext
from cin_validator.rule_engine import IssueLocator
from cin_validator.test_engine import run_rule

# Get tables and columns of interest from the CINTable object defined in rule_engine/__api.py
# Replace ChildIdentifiers with the table name, and LAChildID with the column name you want.

Assessments = CINTable.Assessments
AssessmentFactors = Assessments.AssessmentFactors

# define characteristics of rule
@rule_definition(
    code=8617,
    # replace AssessmentFators with the value in the module column of the excel sheet corresponding to this rule .
    module=CINTable.Assessments,
    # replace the message with the corresponding value for this rule, gotten from the excel sheet.
    message="Code 8A has been returned. This code is not a valid code.",
    # The column names tend to be the words within the < > signs in the github issue description.
    affected_fields=[AssessmentFactors],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    # Replace Assessments with the name of the table you need.
    df = data_container[Assessments]

    # implement rule logic as described by the Github issue. Put the description as a comment above the implementation as shown.

    # Code 8A has been returned as an <AssessmentFactors> (N00181) code
    failing_indices = df[df[AssessmentFactors]=='8A'].index

    # Replace ChildIdentifiers and LAchildID with the table and column name concerned in your rule, respectively.
    # If there are multiple columns or table, make this sentence multiple times.
    rule_context.push_issue(
        table=Assessments, field=AssessmentFactors, row=failing_indices
    )


def test_validate():
    # Create some sample data such that some values pass the validation and some fail.
    assessmentfactors = pd.DataFrame([["8B"], ["8A"], ["8A"], [pd.NA]], columns=[AssessmentFactors])

    # Run rule function passing in our sample data
    result = run_rule(validate, {Assessments: assessmentfactors})

    # The result contains a list of issues encountered
    issues = list(result.issues)
    # replace 2 with the number of failing points you expect from the sample data.
    assert len(issues) == 2
    # replace the table and column name as done earlier.
    # The last numbers represent the index values where you expect the sample data to fail the validation check.
    assert issues == [
        IssueLocator(CINTable.Assessments, AssessmentFactors, 1),
        IssueLocator(CINTable.Assessments, AssessmentFactors, 2),
    ]

    # Check that the rule definition is what you wrote in the context above.

    # replace 8500 with the rule code and put the appropriate message in its place too.
    assert result.definition.code == 8617
    assert result.definition.message == "Code 8A has been returned. This code is not a valid code."