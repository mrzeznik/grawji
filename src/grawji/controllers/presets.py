"""Controller for per-image preset assignment."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from grawji import sidecar
from grawji.catalog import Entry


class PresetFolder(Protocol):
    """The part of the folder model preset applying needs."""

    def entry_for(self, path: str) -> Entry | None:
        """The entry behind a path."""

    def reread_sidecar(self, path: str) -> Entry | None:
        """Refresh one frame's badges after a sidecar edit."""


class PresetController:
    """Store preset names in the images they target, one sidecar each.

    Only the preset's name is written; the recipe itself lives in the
    global library, so applying is cheap and never copies parameters.
    """

    def __init__(
        self,
        *,
        folder: PresetFolder,
        targets: Callable[[], list[str]],
        on_changed: Callable[[list[str]], None] | None = None,
    ) -> None:
        """Wire the controller to the folder.

        Args:
            folder: Where the entries live.
            targets: The images a menu or action applies the preset to.
            on_changed: Called with the paths whose preset changed.
        """
        self._folder = folder
        self._targets = targets
        self._on_changed = on_changed

    def apply(
        self, name: str | None, paths: list[str] | None = None
    ) -> list[str]:
        """Store name (None clears) in every target's sidecar.

        Returns the paths whose stored name actually changed, after
        refreshing their badges and reporting them through on_changed.
        """
        wanted = list(paths) if paths is not None else self._targets()
        changed = []
        for path in wanted:
            if self._folder.entry_for(path) is None:
                continue
            if sidecar.load_recipe_name(path) == name:
                continue
            sidecar.save_recipe_name(path, name)
            self._folder.reread_sidecar(path)
            changed.append(path)
        if changed and self._on_changed is not None:
            self._on_changed(changed)
        return changed
