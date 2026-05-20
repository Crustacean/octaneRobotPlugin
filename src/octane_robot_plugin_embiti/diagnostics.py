"""Small runtime diagnostics for verifying the installed updater."""

from __future__ import annotations

from .version import DISPLAY_VERSION, __version__


def main() -> None:
    import octane_robot_plugin_embiti

    print(f"Octane updater version: {DISPLAY_VERSION}")
    print(f"Package version: {__version__}")
    print(f"Package path: {octane_robot_plugin_embiti.__file__}")


if __name__ == "__main__":
    main()
