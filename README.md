# missing-aur

A curated collection of Arch Linux packages missing from the AUR — automatically kept up to date.

## Packages

![maintained here](https://img.shields.io/badge/maintained%20here-blue?style=flat-square) ![external AUR package](https://img.shields.io/badge/external%20AUR%20package-purple?style=flat-square)

| App | Packages |
|---|---|
| **[crunchyroll-downloader](https://github.com/CuteTenshii/crunchyroll-downloader)**<br>Downloads anime from Crunchyroll and outputs them in a MKV file | [![crunchyroll-downloader-bin](https://img.shields.io/aur/version/crunchyroll-downloader-bin?style=flat-square&label=crunchyroll-downloader-bin)](https://aur.archlinux.org/packages/crunchyroll-downloader-bin) |
| **[beammp-launcher](https://github.com/BeamMP/BeamMP-Launcher)**<br>Multiplayer launcher/client for BeamNG.drive | [![beammp-launcher](https://img.shields.io/aur/version/beammp-launcher?style=flat-square&label=beammp-launcher)](https://aur.archlinux.org/packages/beammp-launcher) [![beammp-launcher-git](https://img.shields.io/aur/version/beammp-launcher-git?style=flat-square&label=beammp-launcher-git&color=purple)](https://aur.archlinux.org/packages/beammp-launcher-git) |
| **[ferrumc](https://github.com/ferrumc-rs/ferrumc)**<br>A reimplementation of the Minecraft server in Rust | [![ferrumc-bin](https://img.shields.io/aur/version/ferrumc-bin?style=flat-square&label=ferrumc-bin)](https://aur.archlinux.org/packages/ferrumc-bin) [![ferrumc-git](https://img.shields.io/aur/version/ferrumc-git?style=flat-square&label=ferrumc-git&color=purple)](https://aur.archlinux.org/packages/ferrumc-git) |
| **[glitchtip-cli](https://gitlab.com/glitchtip/glitchtip-cli)**<br>Open source CLI for GlitchTip | [![glitchtip-cli](https://img.shields.io/aur/version/glitchtip-cli?style=flat-square&label=glitchtip-cli)](https://aur.archlinux.org/packages/glitchtip-cli) [![glitchtip-cli-bin](https://img.shields.io/aur/version/glitchtip-cli-bin?style=flat-square&label=glitchtip-cli-bin)](https://aur.archlinux.org/packages/glitchtip-cli-bin) |
| **[kibo](https://kiboanime.app)**<br>Application for watching anime | [![kibo-appimage](https://img.shields.io/aur/version/kibo-appimage?style=flat-square&label=kibo-appimage)](https://aur.archlinux.org/packages/kibo-appimage) |
| **[layerbase](https://layerbase.com)**<br>A beautiful GUI for managing all your local databases | [![layerbase-bin](https://img.shields.io/aur/version/layerbase-bin?style=flat-square&label=layerbase-bin)](https://aur.archlinux.org/packages/layerbase-bin) |
| **[kissmp](https://github.com/TheHellBox/KISS-multiplayer)**<br>Multiplayer mod for BeamNG.drive | [![kissmp-bridge-bin](https://img.shields.io/aur/version/kissmp-bridge-bin?style=flat-square&label=kissmp-bridge-bin)](https://aur.archlinux.org/packages/kissmp-bridge-bin) [![kissmp-server-bin](https://img.shields.io/aur/version/kissmp-server-bin?style=flat-square&label=kissmp-server-bin)](https://aur.archlinux.org/packages/kissmp-server-bin) |
| **[murmure](https://github.com/Kieirra/murmure)**<br>Fully local, private speech-to-text with LLM post-processing | [![murmure-bin](https://img.shields.io/aur/version/murmure-bin?style=flat-square&label=murmure-bin)](https://aur.archlinux.org/packages/murmure-bin) [![murmure](https://img.shields.io/aur/version/murmure?style=flat-square&label=murmure&color=purple)](https://aur.archlinux.org/packages/murmure) |
| **[psst](https://github.com/jpochyla/psst)**<br>Fast and multi-platform Spotify client with native GUI | [![psst-bin](https://img.shields.io/aur/version/psst-bin?style=flat-square&label=psst-bin)](https://aur.archlinux.org/packages/psst-bin) [![psst-git](https://img.shields.io/aur/version/psst-git?style=flat-square&label=psst-git&color=purple)](https://aur.archlinux.org/packages/psst-git) |
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

- [🤝 Claim ownership](https://github.com/Cleboost/missing-aur/issues/new?template=ownership-claim.yml) — we transfer the AUR package to you and remove it from this repository. You take over maintenance from there.
- ❤️ **Let us handle it** — happy for missing-aur to keep maintaining the AUR package? Just say so and we'll take care of everything, nothing to do on your end.
- [🗑️ Request removal](https://github.com/Cleboost/missing-aur/issues/new?template=removal-request.yml) — we orphan or delete the AUR package entirely and remove it from this repository.

All requests will be handled promptly.
