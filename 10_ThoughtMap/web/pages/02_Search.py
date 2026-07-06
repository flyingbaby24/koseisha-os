def parameters_to_frame(parameters):
    rows = []
    for p in parameters or []:
        rows.append({
            "parameter": p.get("key", ""),
            "value": p.get("value", 0),
        })
    return pd.DataFrame(rows)


def author_summary(df):
    if df.empty or "author" not in df.columns:
        return pd.DataFrame()
    return (
        df[df["author"] != ""]
        .groupby("author", as_index=False)
        .agg(
            works_count=("doc_id", "count"),
            best_similarity=("similarity", "max"),
        )
        .sort_values(["best_similarity", "works_count"], ascending=False)
    )
