# missing-aur

A curated collection of Arch Linux packages missing from the AUR — automatically kept up to date.

## Packages

| App | Packages |
|---|---|
| **[ferrumc](https://github.com/ferrumc-rs/ferrumc)**<br>A reimplementation of the Minecraft server in Rust | [![ferrumc-bin](https://img.shields.io/aur/version/ferrumc-bin?style=flat-square&label=ferrumc-bin)](https://aur.archlinux.org/packages/ferrumc-bin) |
| **[kibo](https://kiboanime.app)**<br>Application for watching anime | [![kibo-appimage](https://img.shields.io/aur/version/kibo-appimage?style=flat-square&label=kibo-appimage)](https://aur.archlinux.org/packages/kibo-appimage) |
| **[kissmp](https://github.com/TheHellBox/KISS-multiplayer)**<br>Multiplayer mod for BeamNG.drive | [![kissmp-bridge-bin](https://img.shields.io/aur/version/kissmp-bridge-bin?style=flat-square&label=kissmp-bridge-bin)](https://aur.archlinux.org/packages/kissmp-bridge-bin) [![kissmp-server-bin](https://img.shields.io/aur/version/kissmp-server-bin?style=flat-square&label=kissmp-server-bin)](https://aur.archlinux.org/packages/kissmp-server-bin) |
| **[psst](https://github.com/jpochyla/psst)**<br>Fast and multi-platform Spotify client with native GUI | [![psst-bin](https://img.shields.io/aur/version/psst-bin?style=flat-square&label=psst-bin)](https://aur.archlinux.org/packages/psst-bin) |
| **[temper](https://github.com/temper-mc/temper)**<br>Stupidly fast open-source Minecraft server written in Rust | [![temper-bin](https://img.shields.io/aur/version/temper-bin?style=flat-square&label=temper-bin)](https://aur.archlinux.org/packages/temper-bin) [![temper-git](https://img.shields.io/aur/version/temper-git?style=flat-square&label=temper-git)](https://aur.archlinux.org/packages/temper-git) |

## How it works

A GitHub Action runs every night and:

1. Runs the `versionChecker` of each package against the upstream source
2. If a new version is found, regenerates the PKGBUILD and updates the checksums
3. Pushes the updated package to the AUR
4. Commits the version bump to this repo

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to add a new package. The short version: create `packages/<app>/manifest.yaml`, run `python3 manage.py generate packages/<app>`, done.

## Upstream maintainers

All packages in this repository are maintained on a best-effort basis for software that has no AUR presence. We genuinely enjoy maintaining these packages and keeping them up to date for the community. If you are the upstream author or maintainer of a packaged project, you have three options — just open a GitHub issue:

- **Claim ownership** — we transfer the AUR package to you and remove it from this repository. You take over maintenance from there.
- **Let us handle it** — happy for missing-aur to keep maintaining the AUR package? Just say so and we'll take care of everything, nothing to do on your end.
- **Request removal** — we orphan or delete the AUR package entirely and remove it from this repository.

All requests will be handled promptly.
