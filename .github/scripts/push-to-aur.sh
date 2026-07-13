#!/usr/bin/env bash
# Push a generated package directory to its AUR repository.
# Usage: push-to-aur.sh <pkg_dir> <aur_username> <aur_email> [commit_message]
#
# Expects GIT_SSH_COMMAND to be set in the environment (SSH key already configured).
set -euo pipefail
set -x

pkg_dir="$1"
aur_username="$2"
aur_email="$3"
commit_msg="${4:-}"

pkgbuild="$pkg_dir/PKGBUILD"
[ -f "$pkgbuild" ] || { echo "No PKGBUILD found in $pkg_dir"; exit 1; }

pkgname=$(grep -oP '^pkgname=\K.*' "$pkgbuild")
pkgver=$(grep -oP '^pkgver=\K.*' "$pkgbuild")
pkgrel=$(grep -oP '^pkgrel=\K.*' "$pkgbuild")

if [[ "$pkgver" == "null" || ! "$pkgver" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]]; then
  echo "Refusing to push invalid pkgver: ${pkgver}"
  exit 1
fi

[ -n "$commit_msg" ] || commit_msg="Update to ${pkgver}-${pkgrel}"

echo "::group::Pushing $pkgname to AUR"

git clone "aur@aur.archlinux.org:${pkgname}.git" aur_repo
find aur_repo -maxdepth 1 ! -name ".git" ! -name "aur_repo" -exec rm -rf {} +
cp "$pkg_dir/PKGBUILD" aur_repo/
cp "$pkg_dir/.SRCINFO" aur_repo/

{ grep -E '^\s+source = ' "$pkg_dir/.SRCINFO" || true; } | grep -v '://' | sed 's/.*= //' | while read -r src; do
  [[ "$src" != *"::"* ]] && [ -f "$pkg_dir/$src" ] && cp "$pkg_dir/$src" aur_repo/
done || true

cd aur_repo
git config user.name "$aur_username"
git config user.email "$aur_email"
git add -A

if git diff --staged --quiet; then
  echo "No changes for ${pkgname}"
else
  git commit -m "$commit_msg"
  git push origin HEAD:master
  echo "Pushed ${pkgname} to AUR"
fi

cd ..
rm -rf aur_repo

echo "::endgroup::"
