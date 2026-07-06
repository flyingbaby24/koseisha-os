        file_name="thoughtmap_clusters.csv",
        mime="text/csv"
    )

    # -------------------------
    # Cluster Labels
    # -------------------------
    label_bytes = json.dumps(
        labels,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    st.download_button(
        "Download cluster labels JSON",
        label_bytes,
        file_name="cluster_labels.json",
        mime="application/json"
    )

    # -------------------------
    # Filter Scores
    # -------------------------
    if filter_score_df is not None:

        filter_bytes = filter_score_df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            "Download filter scores CSV",
            filter_bytes,
            file_name="thoughtmap_filter_scores.csv",
            mime="text/csv"
        )

        try:
            _make_filter_scores, make_parameter_scores = require_thought_composition()
            parameter_score_df = make_parameter_scores(df, filter_score_df)
        except ValueError:
            parameter_score_df = None

        if parameter_score_df is not None:
            parameter_score_bytes = parameter_score_df.to_csv(
                index=False,
                encoding="utf-8-sig"
            ).encode("utf-8-sig")

            st.download_button(
                "Download parameter scores CSV",
                parameter_score_bytes,
                file_name="parameter_scores.csv",
                mime="text/csv"
            )

    # -------------------------
    # Selected Filters
    # -------------------------
    category_bytes = json.dumps(
        categories,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    st.download_button(
        "Download selected filters JSON",
        category_bytes,
        file_name="selected_filters.json",
        mime="application/json"
    )

    # ==========================================================
    # Thought Composition Export
    # ==========================================================
    if filter_score_df is not None:

        status_df = make_status_profile(filter_score_df)

        st.markdown("---")
        st.subheader("Thought Composition Export")

        # -------------------------
        # Composition PNG
        # -------------------------
        document_title = (
            docs[0]["title"]
            if len(docs) == 1
            else f"{len(docs)} Documents"
        )

        fig = plot_status_bar(
            status_df,
            title=document_title
        )

        png_buffer = io.BytesIO()

        fig.savefig(
            png_buffer,
            format="png",
            dpi=300,
            bbox_inches="tight"
        )

        png_buffer.seek(0)

        safe_title = (
            docs[0]["title"]
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            if len(docs) == 1
            else "multi_document"
        )

        st.download_button(
            "Download Composition Chart PNG",
            png_buffer,
            file_name=f"{safe_title}_thought_composition.png",
            mime="image/png"
        )

        # -------------------------
        # Composition Profile CSV
        # -------------------------
        profile_df = pd.DataFrame([
            {
                "profile_class": infer_profile_class(status_df)[0],
                **{
                    row["parameter"]: row["share_%"]
                    for _, row in status_df.iterrows()
                }
            }
        ])

        profile_csv = profile_df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            "Download Composition Profile CSV",
            profile_csv,
            file_name=f"{safe_title}_thought_composition_profile.csv",
            mime="text/csv"
        )
