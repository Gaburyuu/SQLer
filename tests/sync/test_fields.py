import pytest
from sqler.query import SQLerField, SQLerExpression


def test_comparison_operators():
    """check all the operator overloads for sql and params"""
    length = SQLerField("length")
    seq = SQLerField("sequence")
    # added an == method for sqler expresion so we can verify this idk
    assert (length == 18) == SQLerExpression("JSON_EXTRACT(data, '$.length') = ?", [18])
    assert (length != 10) == SQLerExpression(
        "JSON_EXTRACT(data, '$.length') != ?", [10]
    )
    assert (length > 5) == SQLerExpression("JSON_EXTRACT(data, '$.length') > ?", [5])
    assert (length >= 2) == SQLerExpression("JSON_EXTRACT(data, '$.length') >= ?", [2])
    assert (length < 3) == SQLerExpression("JSON_EXTRACT(data, '$.length') < ?", [3])
    assert (length <= 4) == SQLerExpression("JSON_EXTRACT(data, '$.length') <= ?", [4])
    assert (seq == "ACGT") == SQLerExpression(
        "JSON_EXTRACT(data, '$.sequence') = ?", ["ACGT"]
    )


def test_json_path_and_nesting():
    """json path building w/ [] and /"""
    specs = SQLerField("specs")
    bases = specs["bases"]
    tag = specs / "tag"
    assert bases == SQLerField(["specs", "bases"])
    assert tag == SQLerField(["specs", "tag"])
    assert (bases == 10).sql == "JSON_EXTRACT(data, '$.specs.bases') = ?"
    assert (tag == "A").sql == "JSON_EXTRACT(data, '$.specs.tag') = ?"


def test_contains_isin_like():
    """check contains, isin, like helpers work and build right sql"""
    tag = SQLerField("tags")
    expr = tag.contains("exon")
    assert expr.sql == "JSON_EXTRACT(data, '$.tags') LIKE ?"
    assert expr.params == ["%exon%"]

    expr2 = tag.isin(["exon", "intron", "utr"])
    assert expr2.sql == "JSON_EXTRACT(data, '$.tags') IN (?, ?, ?)"
    assert expr2.params == ["exon", "intron", "utr"]

    expr3 = tag.like("exon%")
    assert expr3.sql == "JSON_EXTRACT(data, '$.tags') LIKE ?"
    assert expr3.params == ["exon%"]


def test_fields_make_the_same_way():
    """make sure the paths are working because why not"""
    seq = SQLerField("sequence")
    seq2 = SQLerField(["sequence"])
    region = SQLerField(["sequence", "region"])
    assert seq.path == seq2.path
    assert seq.path != region.path


def test_isin_empty_raises():
    """field.isin([]) should raise ValueError"""
    oligo_type = SQLerField("type")
    with pytest.raises(ValueError):
        oligo_type.isin([])


def test_real_field_works_with_oligo_db(oligo_db):
    """integration: make sure field can be used in real queries on oligos table"""
    # insert some oligos
    oligo_db.insert_document("oligos", {"length": 18, "sequence": "ACGTACGTACGTACGTAC"})
    oligo_db.insert_document(
        "oligos", {"length": 20, "sequence": "CGTAAAGGGTTTCCCAAAGG", "tag": "exon"}
    )
    oligo_db.insert_document("oligos", {"length": 15, "sequence": "GGGTTTAAACCCGGG"})

    length = SQLerField("length")
    tag = SQLerField("tag")
    # query for oligos with length > 16
    expr = length > 16
    results = oligo_db.execute_sql(
        f"SELECT _id, data FROM oligos WHERE {expr.sql}", expr.params
    )
    docs = [d for d in results]
    assert all(doc["length"] > 16 for doc in docs)

    # query for oligos with tag = 'exon'
    expr = tag == "exon"
    results = oligo_db.execute_sql(
        f"SELECT _id, data FROM oligos WHERE {expr.sql}", expr.params
    )
    docs = [d for d in results]
    assert all(doc.get("tag") == "exon" for doc in docs)
