import os
from pathlib import Path

VOLUME_PATH = os.environ.get("FILES_VOLUME_PATH", "")


def save_upload(uploaded_file, subfolder, record_id):
    """
    Save an uploaded file's bytes to the Unity Catalog Volume.
    subfolder: e.g. "resumes" or "job_descriptions"
    record_id: the candidate/job row id, used to avoid filename collisions
    Returns the full volume path, or None if no volume is configured
    (e.g. running locally without the resource attached).
    """
    if not VOLUME_PATH:
        return None

    target_dir = Path(VOLUME_PATH) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{record_id}_{uploaded_file.name}"
    target_path = target_dir / safe_name

    uploaded_file.seek(0)  # file_parsing.extract_text already read it once
    with open(target_path, "wb") as f:
        f.write(uploaded_file.read())

    return str(target_path)
