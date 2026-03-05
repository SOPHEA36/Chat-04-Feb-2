from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_preowned_csv_path() -> Path:
    return (
        get_project_root()
        / "data_preowned"
        / "csv_preowned"
        / "preowned_master.csv"
    )