"""
jcl_oracle — an execution-semantics oracle for z/OS JCL job streams.

This package is the *ground-truth* side of the RELIC evaluation. It is
deliberately independent of the system under test:

* it imports nothing from ``legacy_contract`` (RELIC) or ``baselines``
  (enforced by ``tests/oracle/test_oracle_independence.py``);
* it has its own lexer, its own statement model and its own semantics;
* it never sees RELIC's contracts, diffs, or risk reports.

Given two versions of a JCL file it simulates both under a set of
return-code / abend scenarios and compares externally observable behaviour
(see ``docs/evaluation/ORACLE_SPECIFICATION.md``). The verdict is one of

    DIFFERENT     — some observable differs in some scenario
    EQUIVALENT    — no observable differs, and every step whose position,
                    guard or presence changed is fully modelled
    UNDETERMINED  — no modelled observable differs, but a changed step runs a
                    program whose side effects the oracle cannot model
"""

from jcl_oracle.judge import Verdict, compare_versions, describe_file
from jcl_oracle.lexer import Statement, lex

__all__ = ["Verdict", "compare_versions", "describe_file", "Statement", "lex"]
