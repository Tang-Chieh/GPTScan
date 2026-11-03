"""A rule's negative result is not a compiler/model/infrastructure failure."""


class CandidateRejected(ValueError):
    """Expected, explicit rejection by a configured rule predicate."""


def require_rule_condition(condition, message):
    if not condition:
        raise CandidateRejected(message)
