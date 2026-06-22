# Contributing

Adding a package means writing one `manifest.yaml`. There are no templates and
no hidden magic: YAML keys map 1:1 to standard PKGBUILD fields, and the build
steps are plain bash.

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

## Minimal example (single variant)

```yaml
name: foo
url: https://github.com/author/foo
license: MIT

variants:
  bin:
    pkgver: "1.2.3"
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
| `pkgver` | `0` (for git variants with a `pkgver_func`) |

> **New packages — force the first AUR push:** when submitting a brand-new
> package, set `pkgver: "0"` even for `-bin` variants. The CI compares the
> manifest version against the AUR and only pushes when they differ. Since the
> AUR package doesn't exist yet, starting at `0` guarantees the bot picks it up,
> bumps to the real version, and performs the initial push. If you set the real
> version right away, the bot sees no difference and never creates the AUR package.
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

Files like `.patch` or `.png` placed in `packages/<app>/` are copied into the
build dir automatically and pushed to the AUR repo alongside the PKGBUILD. They
can be referenced by filename in `source`:

```yaml
source:
  - "foo-${pkgver}.tar.gz::https://..."
  - foo.patch          # local file in packages/foo/
```

For simple text files like `.desktop` entries, prefer inlining the content
directly in `package()` via a heredoc — no extra file needed anywhere:

```yaml
package: |
  # ... other install commands ...
  install -Dm644 /dev/stdin "${pkgdir}/usr/share/applications/foo.desktop" << 'EOF'
  [Desktop Entry]
  Name=Foo
  Exec=foo
  Icon=foo
  Type=Application
  Categories=Utility;
  EOF
```

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
- Clear commit messages: `feat: add foo-bin`, `fix: update kissmp versionChecker`.
- Run `python3 manage.py generate packages/<app>` locally and check the PKGBUILD before submitting.
- **Don't forget to add the new app to the table in `README.md`** (one row per app, badges for each variant).
  - Badges for packages maintained here use the default blue color.
  - If other AUR packages exist for the same app (e.g. a `-git` you don't maintain), add their badges too using `&color=purple` — so users know they exist but aren't managed by this repo.
  - Forgetting external badges is no big deal — they're purely informational and can be added later.
