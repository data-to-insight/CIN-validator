from typing import Mapping

import pandas as pd

from cin_validator.rule_engine import CINTable, RuleContext, RuleType, rule_definition
from cin_validator.test_engine import run_rule

Disabilities = CINTable.Disabilities
Disability = Disabilities.Disability
LAchildID = Disabilities.LAchildID


# define characteristics of rule
@rule_definition(
    code="2888Q",
    rule_type=RuleType.QUERY,
    module=CINTable.Disabilities,
    message="Please check and either amend or provide a reason: Only one disability code is recorded per child and multiple disabilities should be recorded where possible.",
    affected_fields=[Disability],
)
def validate(
    data_container: Mapping[CINTable, pd.DataFrame], rule_context: RuleContext
):
    df = data_container[Disabilities]

    # LOGIC
    # Excluding children where <Disability> (N00099) is ‘NONE’, within a local authority, one or more children should have more than one disability recorded.
    # Validation should be triggered at LA level, not child level, if all children who are recorded as having a disability have only 1 disability code recorded.

    # remove "NONE" values
    disability_none = df[Disability] == "NONE"
    df = df[disability_none]

    disability_count = df.groupby(LAchildID)[Disability].count()
    # maximum number of disabilities recorded per child should be > 1

    if disability_count.max() <= 1:
        rule_context.push_la_level(
            rule_context.definition.code, rule_context.definition.message
        )
    else:
        pass


def test_validate():
    sample_disabilities = pd.DataFrame(
        [
            {
                LAchildID: "child1",
                Disability: "NONE",
            },
            {LAchildID: "child1", Disability: "aaaa"},  # child1 : disability_count == 1
            {LAchildID: "child2", Disability: "bbbb"},  # child2 : disability_count == 1
            {LAchildID: "child2", Disability: pd.NA},
            {LAchildID: "child4", Disability: "cc"},  # child4 : disability_count == 1
        ]
    )

    # Run rule function passing in our sample data
    result = run_rule(validate, {Disabilities: sample_disabilities})

    assert result.la_issues == (
        "2888Q",
        "Please check and either amend or provide a reason: Only one disability code is recorded per child and multiple disabilities should be recorded where possible.",
    )
