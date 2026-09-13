"""Import all CARLA results from data/raw into SQLite."""

from pathlib import Path

from importer import import_results_directory


project_root = Path(__file__).parent
results_directory = project_root / "data" / "raw"
database_path = project_root / "data" / "test_health.db"

summary = import_results_directory(database_path, results_directory)

print("CARLA directory import complete")
print(f"- Files seen: {summary.files_seen}")
print(f"- Imported: {summary.files_imported}")
print(f"- Duplicates: {summary.files_duplicated}")
print(f"- Rejected: {summary.files_rejected}")

for error in summary.errors:
    print(f"- Error: {error}")
