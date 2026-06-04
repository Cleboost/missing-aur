#!/usr/bin/env bash
set -euo pipefail

get_json_val() {
  local file="$1"
  local key="$2"
  jq -r ".$key // empty" "$file"
}

get_json_array() {
  local file="$1"
  local key="$2"
  if jq -e ".$key | select(type == \"array\")" "$file" >/dev/null 2>&1; then
    jq -r ".$key | map(\"\\\"\" + . + \"\\\"\") | join(\" \")" "$file"
  else
    echo ""
  fi
}

get_json_block() {
  local file="$1"
  local key="$2"
  jq -r "if .$key == null then empty elif (.$key | type) == \"array\" then .$key[] else .$key end" "$file"
}

write_function() {
  local name="$1"
  local file="$2"
  local key="$3"
  
  local body
  body=$(get_json_block "$file" "$key")
  if [[ -n "$body" ]]; then
    echo "${name}() {" >> PKGBUILD
    while IFS= read -r line; do
      local trimmed
      trimmed=$(echo "$line" | xargs)
      if [[ -z "$trimmed" || "$trimmed" == "EOF" || "$trimmed" == "EOF "* ]]; then
        echo "$line" >> PKGBUILD
      else
        if [[ "$line" =~ ^[[:space:]] ]]; then
          echo "$line" >> PKGBUILD
        else
          echo "  $line" >> PKGBUILD
        fi
      fi
    done <<< "$body"
    echo "}" >> PKGBUILD
    echo "" >> PKGBUILD
  fi
}

generate_pkgbuild() {
  local manifest_path="$1"
  
  echo "# Maintainer: Cleboost <clement.balarot@gmail.com> (missing-aur project)" > PKGBUILD
  echo "# Contributor: missing-aur project <https://github.com/Cleboost/missing-aur>" >> PKGBUILD
  echo "" >> PKGBUILD

  for field in pkgname pkgver pkgrel; do
    local val
    val=$(get_json_val "$manifest_path" "$field")
    if [[ -n "$val" ]]; then
      echo "$field=$val" >> PKGBUILD
    fi
  done

  for field in pkgdesc url; do
    local val
    val=$(get_json_val "$manifest_path" "$field")
    if [[ -n "$val" ]]; then
      echo "$field=\"$val\"" >> PKGBUILD
    fi
  done

  for field in arch depends makedepends optdepends provides conflicts options; do
    local arr
    arr=$(get_json_array "$manifest_path" "$field")
    if [[ -n "$arr" ]]; then
      echo "$field=($arr)" >> PKGBUILD
    fi
  done

  local license_type
  license_type=$(jq -r '.license | type // empty' "$manifest_path")
  if [[ "$license_type" == "array" ]]; then
    local lic
    lic=$(get_json_array "$manifest_path" "license")
    echo "license=($lic)" >> PKGBUILD
  elif [[ "$license_type" == "string" ]]; then
    local lic
    lic=$(get_json_val "$manifest_path" "license")
    echo "license=(\"$lic\")" >> PKGBUILD
  fi
  echo "" >> PKGBUILD

  local source_type
  source_type=$(jq -r '.source | type // empty' "$manifest_path")
  if [[ "$source_type" == "object" ]]; then
    for arch in $(jq -r '.source | keys[]' "$manifest_path"); do
      local srcs
      srcs=$(jq -r ".source.$arch | map(\"\\\"\" + . + \"\\\"\") | join(\" \")" "$manifest_path")
      echo "source_${arch}=($srcs)" >> PKGBUILD
    done
  elif [[ "$source_type" == "array" ]]; then
    local srcs
    srcs=$(get_json_array "$manifest_path" "source")
    echo "source=($srcs)" >> PKGBUILD
  fi

  local has_sha256
  has_sha256=$(jq -e '.sha256sums' "$manifest_path" >/dev/null 2>&1 && echo "yes" || echo "no")
  if [[ "$has_sha256" == "yes" ]]; then
    local sha_type
    sha_type=$(jq -r '.sha256sums | type' "$manifest_path")
    if [[ "$sha_type" == "object" ]]; then
      for arch in $(jq -r '.sha256sums | keys[]' "$manifest_path"); do
        local sums
        sums=$(jq -r ".sha256sums.$arch | map(\"\\\"\" + . + \"\\\"\") | join(\" \")" "$manifest_path")
        echo "sha256sums_${arch}=($sums)" >> PKGBUILD
      done
    else
      local sums
      sums=$(get_json_array "$manifest_path" "sha256sums")
      echo "sha256sums=($sums)" >> PKGBUILD
    fi
  else
    if [[ "$source_type" == "object" ]]; then
      for arch in $(jq -r '.source | keys[]' "$manifest_path"); do
        local len
        len=$(jq -r ".source.$arch | length" "$manifest_path")
        local skips=()
        for ((i=0; i<len; i++)); do skips+=('"SKIP"'); done
        echo "sha256sums_${arch}=(${skips[*]})" >> PKGBUILD
      done
    elif [[ "$source_type" == "array" ]]; then
      local len
      len=$(jq -r '.source | length' "$manifest_path")
      local skips=()
      for ((i=0; i<len; i++)); do skips+=('"SKIP"'); done
      echo "sha256sums=(${skips[*]})" >> PKGBUILD
    fi
  fi
  echo "" >> PKGBUILD

  write_function "pkgver" "$manifest_path" "pkgver_func"
  write_function "prepare" "$manifest_path" "prepare"
  write_function "build" "$manifest_path" "build"
  write_function "package" "$manifest_path" "package"
}

process_package() {
  local pkg_dir="$1"
  local force="${2:-false}"
  local manifest_path="$pkg_dir/manifest.json"

  if [[ ! -f "$manifest_path" ]]; then
    return 1
  fi

  echo "Processing $pkg_dir..."
  local current_ver
  current_ver=$(get_json_val "$manifest_path" "pkgver")
  local pkgname
  pkgname=$(get_json_val "$manifest_path" "pkgname")

  local version_changed=false
  local checker
  checker=$(get_json_val "$manifest_path" "versionChecker")

  if [[ -n "$checker" ]]; then
    echo "  Running version checker..."
    local latest_ver
    latest_ver=$(cd "$pkg_dir" && eval "$checker" || echo "")
    if [[ -n "$latest_ver" && "$latest_ver" != "$current_ver" ]]; then
      echo "  New version found: $current_ver -> $latest_ver"
      jq --arg v "$latest_ver" '.pkgver = $v | .pkgrel = 1' "$manifest_path" > "${manifest_path}.tmp"
      mv "${manifest_path}.tmp" "$manifest_path"
      version_changed=true
    else
      echo "  Already up to date ($current_ver)"
    fi
  fi

  local pkgbuild_path="$pkg_dir/PKGBUILD"
  if [[ "$version_changed" == "true" || "$force" == "true" || ! -f "$pkgbuild_path" ]]; then
    echo "  Generating PKGBUILD..."
    (cd "$pkg_dir" && generate_pkgbuild "manifest.json")

    if [[ -d "$pkg_dir/assets" ]]; then
      cp -f "$pkg_dir"/assets/* "$pkg_dir"/ 2>/dev/null || true
    fi

    if command -v updpkgsums >/dev/null 2>&1; then
      echo "  Updating checksums with updpkgsums..."
      (cd "$pkg_dir" && updpkgsums)
    else
      echo "  Warning: updpkgsums not found, skipping checksum update."
    fi

    if command -v makepkg >/dev/null 2>&1; then
      echo "  Generating .SRCINFO..."
      (cd "$pkg_dir" && makepkg --printsrcinfo > .SRCINFO)
    else
      echo "  Warning: makepkg not found, skipping .SRCINFO generation."
    fi

    echo "UPDATED_PKG: {\"dir\": \"$pkg_dir\", \"pkgname\": \"$pkgname\"}"
  fi
}

find_packages() {
  local pkgs=()
  if [[ -d "packages" ]]; then
    for cat in packages/*; do
      if [[ -d "$cat" ]]; then
        for pkg in "$cat"/*; do
          if [[ -d "$pkg" && -f "$pkg/manifest.json" ]]; then
            pkgs+=("$pkg")
          fi
        done
      fi
    done
  fi
  echo "${pkgs[@]}"
}

usage() {
  echo "Usage: $0 [generate <pkg_dir> [--force] | generate-all [--force] | check-updates [--ci] | clean]"
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

cmd="$1"
shift

case "$cmd" in
  clean)
    echo "Cleaning workspace..."
    find packages -name PKGBUILD -delete
    find packages -name .SRCINFO -delete
    find packages -type d -name src -exec rm -rf {} +
    find packages -type d -name pkg -exec rm -rf {} +
    find packages -name "*.pkg.tar.*" -delete
    find packages -name "*.log" -delete
    find packages -name "*.sig" -delete
    find packages -name "*.tar.gz" -delete
    find packages -name "*.tar.xz" -delete
    find packages -name "*.zip" -delete
    find packages -name "*.AppImage" -delete
    echo "Workspace cleaned!"
    ;;

  generate)
    if [[ $# -lt 1 ]]; then
      echo "Error: Package directory required"
      usage
    fi
    pkg_dir="$1"
    shift
    force=false
    if [[ $# -gt 0 && "$1" == "--force" ]]; then
      force=true
    fi
    process_package "$pkg_dir" "$force"
    ;;

  generate-all)
    force=false
    if [[ $# -gt 0 && "$1" == "--force" ]]; then
      force=true
    fi
    for pkg in $(find_packages); do
      process_package "$pkg" "$force"
    done
    ;;

  check-updates)
    ci=false
    if [[ $# -gt 0 && "$1" == "--ci" ]]; then
      ci=true
    fi

    updated=()
    for pkg in $(find_packages); do
      res=$(process_package "$pkg" "false" | grep "^UPDATED_PKG:" || true)
      if [[ -n "$res" ]]; then
        json_pkg="${res#UPDATED_PKG: }"
        updated+=("$json_pkg")
      fi
    done

    if [[ "$ci" == "true" ]]; then
      joined=""
      if [[ ${#updated[@]} -gt 0 ]]; then
        joined=$(printf ",%s" "${updated[@]}")
        joined="[${joined:1}]"
      else
        joined="[]"
      fi
      echo "::set-output name=packages::${joined}"
      if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "packages=${joined}" >> "$GITHUB_OUTPUT"
      fi
    fi
    ;;

  *)
    usage
    ;;
esac
