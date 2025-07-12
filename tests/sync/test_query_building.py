from sqler.query import SQLerExpression, SQLerQuery


def test_can_build_queries():
    """can we combine expresions into queries?"""

    # make a query obj
    # needs to know the tablename?
    q = SQLerQuery(table="oligos")

    # some expressions
    expression1 = SQLerExpression("length > ?", [20])
    expression2 = SQLerExpression("sequence = ?", ["ACGT"])

    # does it have the correct initial sql?
    assert q.sql == "SELECT data FROM oligos"
    assert q.params == []

    # can we construct sql?
    q = q.filter(expression1)
    assert q.sql == "SELECT data FROM oligos WHERE length > ?"
    assert q.params == [20]

    # should return another query obj that we can chain
    q = q.filter(expression2)
    assert q.sql == "SELECT data FROM oligos WHERE (length > ?) AND (sequence = ?)"
    assert q.params == [20, "ACGT"]
