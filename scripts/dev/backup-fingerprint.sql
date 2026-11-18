-- Only aggregate counts and SHA256 values leave PostgreSQL. No row data is printed.
SET timezone TO 'UTC';
SELECT format(
  $sql$SELECT %1$L || E'\t' || count(*)::text || E'\t' ||
  encode(sha256(convert_to(COALESCE(string_agg(to_jsonb(t)::text, E'\n' ORDER BY to_jsonb(t)::text), ''), 'UTF8')), 'hex')
  FROM %2$I.%3$I AS t;$sql$,
  tablename, schemaname, tablename
)
FROM pg_catalog.pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
\gexec

-- Constraint/index definitions are checked separately by the runner. PostgreSQL
-- can rewrite equivalent varchar-array casts while parsing a restored schema.
