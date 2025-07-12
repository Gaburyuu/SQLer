from sqler.query.expression import SQLerExpression

# sql bits to reuse
LEN_SQL = "length < ?"
TM_SQL = "tm < ?"
IS_SQL = "modification IS NULL"
LIKE_SQL = "sequence LIKE ?"


def test_and():
    """tests and to combine expressions
    an expression should take sql and parameters
    and-ing them should result in combined sql i hope"""

    # try to combine some sql expressions
    a = SQLerExpression(LEN_SQL, [20])
    b = SQLerExpression(TM_SQL, [50])
    # gonna make sure it can combine two expressions
    combined = a & b

    # should have a .sql that we can inspect
    assert combined.sql == f"({LEN_SQL} AND ({TM_SQL}))"
    # same with .params
    assert combined.params == [20, 50]
