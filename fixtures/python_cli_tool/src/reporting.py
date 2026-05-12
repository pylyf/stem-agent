def summarize_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    columns = set()
    for row in rows:
        columns.update(row.keys())
    return {"row_count": len(rows), "column_count": len(columns)}
