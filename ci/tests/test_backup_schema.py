from ci.backup_schema import canonical_schema_definition as canonical


def test_pg_restore_array_cast_rewrite_is_equivalent():
    source = "CHECK (role::text = ANY (ARRAY['patient'::character varying, 'admin'::character varying]::text[]))"
    restored = "CHECK (role::text = ANY (ARRAY['patient'::character varying::text, 'admin'::character varying::text]))"
    assert canonical(source) == canonical(restored)
    index = "WHERE ((status)::text = ANY ((ARRAY['BOOKED'::character varying, 'COMPLETED'::character varying])::text[]))"
    restored_index = "WHERE ((status)::text = ANY (ARRAY['BOOKED'::character varying::text, 'COMPLETED'::character varying::text]))"
    assert canonical(index) == canonical(restored_index)
    restored_index_with_parentheses = restored_index.replace(
        "'BOOKED'::character varying::text", "('BOOKED'::character varying)::text"
    ).replace("'COMPLETED'::character varying::text", "('COMPLETED'::character varying)::text")
    assert canonical(index) == canonical(restored_index_with_parentheses)
    assert canonical(canonical(source)) == canonical(source)


def test_normalization_preserves_values_cast_bounds_and_operators():
    source = "CHECK (role::text = ANY (ARRAY['patient'::character varying]::text[]))"
    for different in [
        source.replace("patient", "admin"),
        source.replace(" = ", " <> "),
        source.replace("character varying", "character varying(3)"),
        source.replace("character varying", "integer"),
        source.replace("::text[]", "::citext[]"),
    ]:
        assert canonical(source) != canonical(different)
    assert canonical("ARRAY['a''b'::character varying]::text[]") == "ARRAY['a''b'::text]"
    assert (
        canonical("ARRAY['a::character varying'::character varying]::text[]")
        == "ARRAY['a::character varying'::text]"
    )
