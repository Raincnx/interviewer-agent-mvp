from pathlib import Path


class PromptStore:
    def __init__(self, root_dir: Path, version: str) -> None:
        self.root_dir = root_dir
        self.version = version

    @property
    def version_dir(self) -> Path:
        return self.root_dir / "versions" / self.version

    def read(self, prompt_name: str) -> str:
        prompt_path = self.version_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' does not exist for version '{self.version}' at '{prompt_path}'."
            )
        return prompt_path.read_text(encoding="utf-8")
