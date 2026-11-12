"""Tests for storing per-image preset names through the controller."""

from __future__ import annotations

from pathlib import Path

from grawji.catalog import Entry
from grawji.controllers.presets import PresetController
from grawji.sidecar import load_recipe_name, save_recipe_name


class FakeFolder:
    """The folder model, reduced to what preset applying touches."""

    def __init__(self, folder: Path, names: list[str]) -> None:
        """Create one empty RAF per name."""
        self.entries: dict[str, Entry] = {}
        for name in names:
            path = folder / name
            path.write_bytes(b"raf")
            self.entries[str(path)] = Entry(path=str(path), name=name)
        self.reread: list[str] = []

    def entry_for(self, path: str) -> Entry | None:
        """The entry behind a path."""
        return self.entries.get(path)

    def reread_sidecar(self, path: str) -> Entry | None:
        """Refresh the entry and remember the call."""
        self.reread.append(path)
        return self.entries.get(path)


def make(tmp_path: Path, *names: str):
    """A controller over a fake folder, plus the recording lists."""
    folder = FakeFolder(tmp_path, list(names))
    paths = list(folder.entries)
    changed: list[list[str]] = []
    controller = PresetController(
        folder=folder,
        targets=lambda: list(paths[:1]),
        on_changed=changed.append,
    )
    return controller, folder, paths, changed


def test_a_preset_name_is_stored_and_reported(tmp_path: Path) -> None:
    """The sidecar, the badge refresh and the listener all hear of it."""
    controller, folder, paths, changed = make(tmp_path, "a.RAF")
    result = controller.apply("Velvia Warm", paths)
    assert result == paths
    assert load_recipe_name(paths[0]) == "Velvia Warm"
    assert folder.reread == paths
    assert changed == [paths]


def test_the_same_name_again_changes_nothing(tmp_path: Path) -> None:
    """An unchanged preset does not rewrite the sidecar or notify."""
    controller, folder, paths, changed = make(tmp_path, "a.RAF")
    controller.apply("Velvia Warm", paths)
    folder.reread.clear()
    changed.clear()
    assert controller.apply("Velvia Warm", paths) == []
    assert changed == []


def test_clearing_removes_the_key(tmp_path: Path) -> None:
    """Applying None (the shot's own recipe) deletes the stored name."""
    controller, _folder, paths, _changed = make(tmp_path, "a.RAF")
    controller.apply("Velvia Warm", paths)
    assert controller.apply(None, paths) == paths
    assert load_recipe_name(paths[0]) is None


def test_targets_default_to_the_current_selection(tmp_path: Path) -> None:
    """Without explicit paths the controller takes the targets."""
    controller, _folder, paths, _changed = make(tmp_path, "a.RAF", "b.RAF")
    assert controller.apply("CC Neg") == paths[:1]
    assert load_recipe_name(paths[0]) == "CC Neg"
    assert load_recipe_name(paths[1]) is None


def test_unknown_paths_are_skipped(tmp_path: Path) -> None:
    """A path the folder does not know is not written to."""
    controller, _folder, _paths, _changed = make(tmp_path, "a.RAF")
    stranger = str(tmp_path / "outside.RAF")
    Path(stranger).write_bytes(b"raf")
    save_recipe_name(stranger, "keep")
    assert controller.apply("Velvia Warm", [stranger]) == []
    assert load_recipe_name(stranger) == "keep"
