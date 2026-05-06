# Contributing Guidelines

Thank you for considering contributing to `missing-aur`! 

## How to add a new package

To add a new package, please follow these steps:

1. **Create a new directory**: The name should match the base name of the package (e.g., `my-cool-app`).
2. **Add a `PKGBUILD`**: Follow the standard Arch Linux [PKGBUILD](https://wiki.archlinux.org/title/PKGBUILD) guidelines.
3. **Add a `version.sh`**: This script must output the latest version string to `stdout`. It is used by the automation bot to detect updates.
   - Example for GitHub releases: `curl -s https://api.github.com/repos/user/repo/releases/latest | jq -r .tag_name`
4. **Test your package**: Ensure `makepkg` works locally before submitting.

## Pull Request Rules

- **One package per PR**: Each Pull Request should only add or modify a single package.
- **Commit style**: Use clear commit messages like `feat: add my-cool-app`.
- **Validation**: Ensure your `PKGBUILD` and `version.sh` are working correctly. The automation will take care of SHA-256 sums and `.SRCINFO` once merged, but it's better to have them correct from the start.

## Directory Structure

```text
my-cool-app/
├── PKGBUILD
└── version.sh
```
