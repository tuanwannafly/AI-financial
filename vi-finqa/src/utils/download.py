from huggingface_hub import snapshot_download

# Default public release (duplicate of HuuDong03uet/ViFinQA, more downloads)
DEFAULT_REPO_ID = "AIGuruTinix/ViFinQA"


def download_dataset(repo_id: str = DEFAULT_REPO_ID, local_dir: str = "data/raw") -> str:
    """Download full ViFinQA dataset to local_dir and return path."""

    path = snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=local_dir,
    )
    return path
