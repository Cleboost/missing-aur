# missing-aur

A collection of Arch Linux PKGBUILDs for software that is missing or outdated in the official AUR.

## How it works

This repository uses a GitHub Action that runs daily to:
1. Check for new versions using a `version.sh` script in each package directory.
2. Automatically update `pkgver` and `pkgrel` in the `PKGBUILD`.
3. Recalculate SHA-256 checksums.
4. Update `.SRCINFO`.
5. Push updates back to this repository and sync them directly with the AUR.

## Available Packages

- **[kibo-appimage](https://www.kiboanime.app/)**: Kibo Anime AppImage - Application for watching anime.
- **[kissmp-bridge-bin](https://github.com/TheHellBox/KISS-multiplayer)**: Bridge for KissMP, a multiplayer mod for BeamNG.drive (binary version).
- **[kissmp-server-bin](https://github.com/TheHellBox/KISS-multiplayer)**: Server for KissMP, a multiplayer mod for BeamNG.drive (binary version).
- **[psst-bin](https://github.com/jpochyla/psst)**: Fast and multi-platform Spotify client with native GUI (binary version).
- **[temper-bin](https://github.com/temper-mc/temper)**: A stupidly fast open-source Minecraft server, written in Rust (binary version).
- **[temper-git](https://github.com/temper-mc/temper)**: A stupidly fast open-source Minecraft server, written in Rust (git version).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to add new packages.
