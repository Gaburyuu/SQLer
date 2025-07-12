import json
import pytest

from sqler.query import SQLerField, SQLerQuery


@pytest.fixture
def setup_oligos(oligo_db):
    """populate oligos table with various test oligos"""
    oligos = [
        {
            "sequence": "ACGT",
            "length": 4,
            "tm": 12.3,
            "mass": 1.1,
            "tags": ["short", "test"],
        },
        {
            "sequence": "AACCCGGGGTTTT",
            "length": 13,
            "tm": 47.2,
            "mass": 4.2,
            "tags": ["long", "weird"],
        },
        {"sequence": "TTTT", "length": 4, "tm": 10.2, "mass": 1.0, "tags": ["short"]},
        {
            "sequence": "GATTACA",
            "length": 7,
            "tm": 22.0,
            "mass": 2.0,
            "tags": ["movie", "dna"],
        },
        {
            "sequence": "CCGGAA",
            "length": 6,
            "tm": 18.7,
            "mass": 1.7,
            "tags": ["even", "test"],
        },
        {"sequence": "NNNN", "length": 4, "tm": 0.0, "mass": 0.0, "tags": ["mixed"]},
    ]
    for oligo in oligos:
        oligo_db.insert_document("oligos", oligo)
    return oligos


def test_filter_length_gt(oligo_db, setup_oligos):
    length = SQLerField("length")
    q = SQLerQuery("oligos", oligo_db.adapter)
    result = q.filter(length > 6).all()
    oligos = [json.loads(row) for row in result]
    seqs = {o["sequence"] for o in oligos}
    assert "AACCCGGGGTTTT" in seqs
    assert "GATTACA" in seqs
    assert "CCGGAA" not in seqs


def test_and_or_logic(oligo_db, setup_oligos):
    length = SQLerField("length")
    tag = SQLerField("tags")
    q = SQLerQuery("oligos", oligo_db.adapter)
    expr = ((length == 4) & tag.contains("short")) | (tag.contains("movie"))
    rows = [json.loads(j) for j in q.filter(expr).all()]
    seqs = {o["sequence"] for o in rows}
    # Should include "ACGT", "TTTT" (length 4 and short) and "GATTACA" (movie)
    assert "ACGT" in seqs
    assert "TTTT" in seqs
    assert "GATTACA" in seqs


def test_exclude_by_mass(oligo_db, setup_oligos):
    mass = SQLerField("mass")
    q = SQLerQuery("oligos", oligo_db.adapter)
    result = q.exclude(mass == 0.0).all()
    oligos = [json.loads(row) for row in result]
    seqs = {o["sequence"] for o in oligos}
    assert "NNNN" not in seqs
    assert "ACGT" in seqs


def test_order_by_tm_desc(oligo_db, setup_oligos):
    tm = SQLerField("tm")
    q = SQLerQuery("oligos", oligo_db.adapter)
    rows = [json.loads(j) for j in q.order_by("tm", desc=True).all()]
    tms = [o["tm"] for o in rows]
    assert tms == sorted(tms, reverse=True)


def test_limit_two_shortest(oligo_db, setup_oligos):
    length = SQLerField("length")
    q = SQLerQuery("oligos", oligo_db.adapter)
    rows = [json.loads(j) for j in q.order_by("length").limit(2).all()]
    # All your short oligos have length 4
    assert all(o["length"] == 4 for o in rows)
    assert len(rows) == 2


def test_first_returns_one(oligo_db, setup_oligos):
    q = SQLerQuery("oligos", oligo_db.adapter)
    first = q.order_by("sequence").first()
    oligo = json.loads(first)
    assert isinstance(oligo, dict)
    assert "sequence" in oligo


def test_chained_queries_are_immutable(oligo_db, setup_oligos):
    tag = SQLerField("tags")
    q = SQLerQuery("oligos", oligo_db.adapter)
    q1 = q.filter(tag.contains("short"))
    q2 = q1.exclude(SQLerField("sequence") == "ACGT")
    seqs1 = {json.loads(j)["sequence"] for j in q1.all()}
    seqs2 = {json.loads(j)["sequence"] for j in q2.all()}
    assert "ACGT" in seqs1
    assert "ACGT" not in seqs2


def test_in_and_like(oligo_db, setup_oligos):
    seq = SQLerField("sequence")
    q = SQLerQuery("oligos", oligo_db.adapter)
    # any sequence exactly one of these
    expr = seq.isin(["ACGT", "GATTACA"])
    rows = [json.loads(j) for j in q.filter(expr).all()]
    seqs = {o["sequence"] for o in rows}
    assert seqs == {"ACGT", "GATTACA"}
    # pattern matching
    expr2 = seq.like("A%")
    rows2 = [json.loads(j) for j in q.filter(expr2).all()]
    for o in rows2:
        assert o["sequence"].startswith("A")


def test_nested_path(oligo_db):
    # Insert oligo with mz > 900 and labeled "NESTED"
    oligo_db.insert_document(
        "oligos",
        {
            "sample_name": "NESTED",
            "qc": {
                "esi_ms": {
                    "contaminant_peaks": [
                        {
                            "mz": 925.4,
                            "intensity": 4200,
                            "identity": "depurination",
                        },
                        {"mz": 789.5, "intensity": 8700, "identity": "n-1"},
                    ],
                    "analysis_date": "2025-07-10",
                    "instrument": {
                        "model": "Oligotrap 8001",
                        "operator": "OscarLigo",
                    },
                },
            },
        },
    )

    # Insert control oligo with all mz < 900
    oligo_db.insert_document(
        "oligos",
        {
            "sample_name": "CONTROL",
            "qc": {
                "esi_ms": {
                    "contaminant_peaks": [
                        {"mz": 243.12, "intensity": 15000, "identity": "unknown"},
                        {"mz": 789.5, "intensity": 8700, "identity": "n-1"},
                    ],
                    "analysis_date": "2025-07-11",
                    "instrument": {
                        "model": "Oligotrap 8001",
                        "operator": "OscarLigo",
                    },
                },
            },
        },
    )

    # Query for any contaminant peak with mz > 900
    mz = SQLerField(["qc", "esi_ms", "contaminant_peaks", "mz"])
    q = SQLerQuery("oligos", oligo_db.adapter)
    expr = mz > 900
    rows = [json.loads(j) for j in q.filter(expr).all()]

    # Assert only the NESTED oligo was returned
    sequences = {r["sample_name"] for r in rows}
    assert "NESTED" in sequences
    assert "CONTROL" not in sequences


def test_operator_precedence_docstring(oligo_db, setup_oligos):
    seq = SQLerField("sequence")
    q = SQLerQuery("oligos", oligo_db.adapter)
    expr = ((seq == "ACGT") & (seq == "TTTT")) | (seq == "AACCCGGGGTTTT")
    rows = [json.loads(j) for j in q.filter(expr).all()]
    # Only the long one matches (the other AND is never true)
    assert rows[0]["sequence"] == "AACCCGGGGTTTT"
    expr2 = (seq == "ACGT") & ((seq == "TTTT") | (seq == "AACCCGGGGTTTT"))
    rows2 = [json.loads(j) for j in q.filter(expr2).all()]
    # Should be empty
    assert rows2 == []


def test_contains_on_array(oligo_db, setup_oligos):
    tags = SQLerField("tags")
    q = SQLerQuery("oligos", oligo_db.adapter)
    expr = tags.contains("test")
    rows = [json.loads(j) for j in q.filter(expr).all()]
    assert any("test" in o["tags"] for o in rows)


def test_isin_empty_list_raises():
    field = SQLerField("sequence")
    with pytest.raises(ValueError):
        field.isin([])
