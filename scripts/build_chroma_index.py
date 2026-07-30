"""Build or verify the persistent ErgoStudy Chroma collection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chroma_store import build_collection, create_manifest, reopen_and_verify  # noqa: E402
from src.dataset_io import file_sha256, read_json, read_jsonl, write_json  # noqa: E402
from src.embedding_evaluator import package_versions  # noqa: E402
from src.embedding_models import encode_texts, load_embedding_configurations, load_sentence_transformer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Delete only the exact ErgoStudy collection before rebuilding")
    arguments = parser.parse_args()
    processed = PROJECT_ROOT / "data" / "processed"
    records = read_jsonl(processed / "knowledge_corpus.jsonl")
    selected = read_json(processed / "selected_embedding_model.json")
    settings, configurations = load_embedding_configurations(PROJECT_ROOT / "config" / "embedding_models.json")
    configuration = next(item for item in configurations if item.config_id == selected["config_id"])
    model = load_sentence_transformer(
        configuration.model_id,
        selected["device"],
        revision=selected["model_revision"],
        local_files_only=True,
    )
    embeddings = encode_texts(
        model,
        [configuration.format_document(record["retrieval_text"]) for record in records],
        batch_size=int(settings["batch_size"]),
        normalize_embeddings=configuration.normalize_embeddings,
    )
    manifest = create_manifest(
        records=records,
        corpus_sha256=file_sha256(processed / "knowledge_corpus.jsonl"),
        selected_model=selected,
        package_versions=package_versions(),
    )
    write_json(processed / "chroma_index_manifest.json", manifest)
    result = build_collection(
        project_root=PROJECT_ROOT,
        chroma_path=PROJECT_ROOT / "chroma_db",
        records=records,
        embeddings=embeddings,
        manifest=manifest,
        rebuild=arguments.rebuild,
    )
    del model
    persisted = reopen_and_verify(
        project_root=PROJECT_ROOT,
        chroma_path=PROJECT_ROOT / "chroma_db",
        records=records,
        manifest=manifest,
    )
    print(json.dumps({"build": result, "reopened": persisted}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
