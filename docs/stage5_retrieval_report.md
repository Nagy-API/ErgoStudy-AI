# Retrieval report

The frozen `alias_plus_dense` configuration remains unchanged. Five obsolete sensor-only queries were removed, requiring a fresh deterministic split of the 91 remaining legitimate queries: 61 development and 30 final.

The current 30-query final result is Recall@5 `0.9038`, MRR@10 `0.9274`, nDCG@10 `0.9198`, document-family Hit@5 `1.0000`, and subject-family Hit@5 `1.0000`. These metrics belong to the new split and are not directly comparable with the earlier 32-query evaluation.

All retrieved IDs in result artifacts exist in the 463-record corpus, and no evaluation record is present in Chroma.
