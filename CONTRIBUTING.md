# Contributing

Adding a package means writing one `manifest.yaml`. There are no templates and
no hidden magic: YAML keys map 1:1 to standard PKGBUILD fields, and the build
steps are plain bash.

## AI assistants

If you are an AI agent working from this guide:

- **This repo (`missing-aur`)** — proceed on your own: manifest, local assets,
  `README.md` table, `manage.py generate`, commits, and PRs here. No need to ask
  permission for each step unless the user said otherwise.
- **Upstream README PR** — **never** fork the upstream project, edit their
  README, or open a PR there unless the user **explicitly** asks you to. After
  adding a package here, you may briefly mention that an upstream install-doc PR
  is possible — then stop and wait for a clear yes/no.

## Structure

```
packages/
  <app>/
    manifest.yaml      ← everything goes here
    <file>.desktop     ← local assets (optional)
```

The generated subdirectories `packages/<app>/<pkgname>/` (PKGBUILD, .SRCINFO)
are **fully generated** — never edit them by hand, and **never commit them**.
They are produced by `manage.py` on demand locally and by the CI on the server.
Committing them would cause conflicts and drift from what the generator produces.
The `.gitignore` is already configured to ignore them.

## How it works

A manifest declares an app `name` and one or more `variants`. The variant key
is appended to the name to form the package name:

```yaml
name: psst          # the app
variants:
  bin:              # → pkgname = psst-bin
  git:              # → pkgname = psst-git
```

Some variant keys are **reserved** and produce no suffix — the pkgname equals
`name` exactly. Use them when the package follows the AUR convention of having
no suffix (i.e. it is the canonical, non-binary, non-git package):

| Key | Intended use |
|---|---|
| `base` | Compiled from a release tarball (default choice) |
| `stable` | Alias for the same intent |
| `release` | Alias for the same intent |

```yaml
name: foo
variants:
  base:    # → pkgname = foo  (no suffix)
  bin:     # → pkgname = foo-bin
  git:     # → pkgname = foo-git
```

Fields written at the top level are **shared** by every variant. A variant can
override any of them. That's the whole model.

**Avoid duplicating fields across variants.** If a field has the same value in
every variant, hoist it to the top level. Only keep in the variant what actually
differs between variants (e.g. `conflicts`, `pkgver`, `source`).

## New packages — set `pkgver` to `0`

When adding a package that does **not** exist on the AUR yet, set `pkgver: "0"`
in the manifest for **every new variant** (`-bin`, `-appimage`, `base`, etc.) —
**except `-git`**. Git variants derive their version from a `pkgver()` function
and do not use this trick.

The nightly GitHub Action runs each variant's `versionChecker`, compares the
result to `pkgver`, and only pushes to the AUR when they differ. A brand-new
package has no AUR entry yet, so if you write the real upstream version
straight away the bot sees nothing to update and **never creates the AUR
package**.

Starting at `0` guarantees the bot detects a newer version, bumps the manifest,
regenerates the PKGBUILD, and performs the initial push. You do not need to
track the latest version yourself — the `versionChecker` and CI handle that
after merge.

If you already committed the real version by mistake, push a follow-up commit
that sets `pkgver` back to `"0"` (see `fix(murmure-bin): set pkgver to 0 to
trigger initial AUR push`).

## Minimal example (single variant)

```yaml
name: foo
url: https://github.com/author/foo
license: MIT

variants:
  bin:
    pkgver: "0"                     # new -bin package → 0; CI bumps to latest
    pkgdesc: "Short description"
    depends: [gtk3, openssl]
    versionChecker: "curl -s https://api.github.com/repos/author/foo/releases/latest | jq -r '.tag_name' | sed 's/^v//'"
    source:
      - "foo-${pkgver}::${url}/releases/download/v${pkgver}/foo-linux-x86_64"
    package: |
      install -Dm755 "foo-${pkgver}" "${pkgdir}/usr/bin/foo"
```

This produces `packages/foo/foo-bin/PKGBUILD` with pkgname `foo-bin`.

## Multiple variants (shared fields)

```yaml
name: foo
url: https://github.com/author/foo
license: GPL3
arch: [x86_64, aarch64]          # shared by both variants
pkgdesc: "Foo"                    # identical in both → hoist it
provides: [foo]                   # identical in both → hoist it

variants:
  bin:
    pkgver: "1.2.3"
    conflicts: [foo, foo-git]
    versionChecker: "..."
    source:
      - "foo-${pkgver}.tar.gz::${url}/releases/download/v${pkgver}/foo-linux.tar.gz"
    package: |
      install -Dm755 "${srcdir}/foo" "${pkgdir}/usr/bin/foo"

  git:
    depends: [gcc-libs, glibc]
    makedepends: [cargo, git]
    conflicts: [foo, foo-bin]
    source:
      - "foo::git+${url}.git"
    pkgver_func: |
      cd "${srcdir}/foo"
      git describe --long --tags | sed 's/\([^-]*-g\)/r\1/;s/-/./g;s/^v//'
    build: |
      cd "${srcdir}/foo"
      cargo build --release
    package: |
      cd "${srcdir}/foo"
      install -Dm755 "target/release/foo" "${pkgdir}/usr/bin/foo"
```

Variant fields override shared ones. A `git` variant simply omits
`versionChecker` (its version is derived by the `pkgver` function instead).

## Fields

Standard PKGBUILD fields, used as-is:

| YAML | PKGBUILD |
|---|---|
| `pkgname`, `pkgver`, `pkgrel`, `epoch` | unquoted scalars |
| `pkgdesc`, `url` | quoted scalars |
| `arch`, `depends`, `makedepends`, `optdepends`, `provides`, `conflicts`, `replaces`, `options`, `backup`, `groups` | arrays |
| `license` | array |
| `source` | array, or a per-arch map (see below) |

Build functions are written as **multiline bash** strings:

| YAML key | PKGBUILD function |
|---|---|
| `pkgver_func` | `pkgver()` |
| `prepare` | `prepare()` |
| `build` | `build()` |
| `package` | `package()` |

`${pkgver}`, `${srcdir}`, `${pkgdir}`, `${url}`, etc. are interpolated by
makepkg at build time — write them literally.

### Per-architecture sources

```yaml
source:
  x86_64:
    - "foo-${pkgver}-x86_64.tar.gz::${url}/.../foo-x86_64.tar.gz"
  aarch64:
    - "foo-${pkgver}-aarch64.tar.gz::${url}/.../foo-aarch64.tar.gz"
```

## Defaults

Optional when you want the default:

| Field | Default |
|---|---|
| `pkgrel` | `1` |
| `arch` | `[x86_64]` |
| `pkgver` | `0` (default for git variants with a `pkgver_func`; required for all other new packages — see [New packages](#new-packages--set-pkgver-to-0)) |
| `sha256sums` | `SKIP` (filled in automatically by `updpkgsums`) |

## Automatic description suffix

A parenthetical suffix is appended to `pkgdesc` based on the pkgname ending —
don't write it yourself:

| pkgname ends with | appended |
|---|---|
| `-bin` | `(precompiled binary)` |
| `-git` | `(git version)` |
| `-appimage` | `(AppImage)` |

If the description already ends with `)`, nothing is appended. Base variants
(`base`, `stable`, `release`) never receive a suffix.

## Local assets

Files committed in `packages/<app>/` (`.desktop`, `.patch`, icons, etc.) are
copied into the generated build dir by `manage.py`. Reference them in `source`
with a **download URL** — `makepkg` on the AUR must be able to fetch every
source file.

```yaml
source:
  - "foo-${pkgver}.tar.gz::https://upstream.example/foo-${pkgver}.tar.gz"
  - "foo.desktop::https://raw.githubusercontent.com/Cleboost/missing-aur/main/packages/foo/foo.desktop"
```

`push-to-aur.sh` can also copy bare filenames (no URL) into the AUR git repo,
but this repo does not rely on that — always use a raw URL, either from
missing-aur (for files you maintain here) or from upstream (see
`packages/psst/manifest.yaml`).

### Desktop entries (`.desktop`)

**Do not use a heredoc in `package()`.** `manage.py` indents every line inside
build functions, including heredoc content — the installed `.desktop` file ends
up with leading spaces on each line and launchers ignore it.

Instead, commit a `packages/<app>/<app>.desktop` file and reference it in
`source` with a **raw GitHub URL** so AUR users can download it with
`makepkg`:

```yaml
source:
  - "foo-${pkgver}.tar.gz::https://..."
  - "foo.desktop::https://raw.githubusercontent.com/Cleboost/missing-aur/main/packages/foo/foo.desktop"
package: |
  install -Dm644 "${srcdir}/foo.desktop" "${pkgdir}/usr/share/applications/foo.desktop"
```

If upstream already ships a `.desktop` file, point to its raw URL instead (see
`packages/psst/manifest.yaml`).

Packaging-only fixes (desktop entry, install path, etc.) with no upstream version
change require a manual `pkgrel` bump in the manifest. The nightly bot only
resets `pkgrel` to `1` when `pkgver` changes.

## versionChecker

A shell command printing the **latest available version** to stdout. If it
differs from `pkgver`, the manifest is updated and the PKGBUILD regenerated
automatically by the update bot.

```yaml
# GitHub releases
versionChecker: "curl -s https://api.github.com/repos/author/repo/releases/latest | jq -r '.tag_name' | sed 's/^v//'"

# Web scraping
versionChecker: "curl -s https://example.com | grep -oP 'v\\K[0-9.]+' | head -1"
```

## CLI

```bash
python3 manage.py generate packages/foo     # generate one app
python3 manage.py generate-all --force      # regenerate everything
python3 manage.py check-updates             # check + regenerate if newer
python3 manage.py clean                     # remove all generated files
```

## Pull request rules

- **One package per PR.**
- **New AUR packages: set `pkgver: "0"`** on every variant except `-git`, so
  the GitHub Action performs the initial push (see
  [New packages](#new-packages--set-pkgver-to-0)).
- Clear commit messages: `feat: add foo-bin`, `fix: update kissmp versionChecker`.
- Run `python3 manage.py generate packages/<app>` locally and check the PKGBUILD before submitting.
- **Don't forget to add the new app to the table in `README.md`** (one row per app, badges for each variant).
  - Badges for packages maintained here use the default blue color.
  - If other AUR packages exist for the same app (e.g. a `-git` you don't maintain), add their badges too using `&color=purple` — so users know they exist but aren't managed by this repo.
  - Forgetting external badges is no big deal — they're purely informational and can be added later.

## Upstream README PR

Optional follow-up **after** a package is live on the AUR: a small documentation
PR on the upstream project so Arch users can find it. **Human contributors:**
your call. **AI agents:** only do this when the user explicitly asks — see
[AI assistants](#ai-assistants).

Keep the change minimal: one new subsection under the existing Linux /
Installation docs. No code changes, no test plan in the PR body.

Real example: [cdevroe/signboard#48](https://github.com/cdevroe/signboard/pull/48).

### Workflow

1. Fork the upstream repo (if you do not already have one).
2. Create a branch: `docs/arch-linux-aur-install`
3. Add the README subsection below under Installation (or the Linux install
   section — match wherever upstream documents downloads).
4. Commit: `docs: document Arch Linux AUR installation`
5. Open a PR against upstream `main` (or their default branch).

```bash
git checkout -b docs/arch-linux-aur-install
# edit README
git add README.md   # or readme.md — use whatever the upstream repo uses
git commit -m "docs: document Arch Linux AUR installation"
git push -u origin docs/arch-linux-aur-install
gh pr create --repo <upstream-owner>/<upstream-repo> \
  --head Cleboost:docs/arch-linux-aur-install \
  --base main \
  --title "docs: document Arch Linux AUR installation" \
  --body-file /path/to/pr-body.md
```

### README subsection (copy-paste template)

Replace the placeholders, then paste under the upstream install section:

| Placeholder | Example |
|---|---|
| `<AppName>` | `Signboard` |
| `<pkgname>` | `signboard-appimage` |
| `<arch>` | `x86_64` and `aarch64` (or just `x86_64`) |

```markdown
### Arch Linux (AUR)

On Arch Linux and Arch-based distributions, <AppName> is available on the [Arch User Repository](https://aur.archlinux.org/packages/<pkgname>) as `<pkgname>` for <arch>. The package is maintained in the community [`missing-aur`](https://github.com/Cleboost/missing-aur) project and kept up to date with upstream releases.

Install with your preferred AUR helper:

\`\`\`bash
yay -S <pkgname>
# or
paru -S <pkgname>
\`\`\`
```

**Signboard example** (filled in):

```markdown
### Arch Linux (AUR)

On Arch Linux and Arch-based distributions, Signboard is available on the [Arch User Repository](https://aur.archlinux.org/packages/signboard-appimage) as `signboard-appimage` for `x86_64` and `aarch64`. The package is maintained in the community [`missing-aur`](https://github.com/Cleboost/missing-aur) project and kept up to date with upstream releases.

Install with your preferred AUR helper:

\`\`\`bash
yay -S signboard-appimage
# or
paru -S signboard-appimage
\`\`\`
```

### PR title

```
docs: document Arch Linux AUR installation
```

### PR body (copy-paste template)

Replace `<pkgname>` and `<arch>`:

```markdown
## Summary

- Adds an **Arch Linux (AUR)** subsection under Installation in the README
- Documents the community-maintained [`<pkgname>`](https://aur.archlinux.org/packages/<pkgname>) package for <arch>
- Includes example install commands for common AUR helpers (`yay`, `paru`)

The package is maintained in [missing-aur](https://github.com/Cleboost/missing-aur) and updated automatically from upstream releases.
```

**Signboard example** (filled in):

```markdown
## Summary

- Adds an **Arch Linux (AUR)** subsection under Installation in `readme.md`
- Documents the community-maintained [`signboard-appimage`](https://aur.archlinux.org/packages/signboard-appimage) package for `x86_64` and `aarch64`
- Includes example install commands for common AUR helpers (`yay`, `paru`)

The package is maintained in [missing-aur](https://github.com/Cleboost/missing-aur) and updated automatically from upstream GitHub releases.
```

### Notes

- Match the upstream README filename and heading style (`README.md` vs `readme.md`,
  `## Installation` vs `### Linux`).
- Only document variants actually published on the AUR from this repo.
- If upstream already lists distro packages (Homebrew, Flathub, etc.), place the
  AUR block alongside them — do not replace their existing install flow.
- If the maintainer declines or ignores the PR, the AUR package still works;
  this is optional outreach, not a blocker.
