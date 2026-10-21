#!/usr/bin/env python3
"""
generate-index.py

Generates legacy Tachiyomi extension repository metadata files:
- index.json (pretty-printed JSON array)
- index.min.json (minified single-line JSON array)
- repo.json (repository metadata for Tachiyomi 0.15.2+ and forks)
- Extracts extension icons to icon/{pkg}.png

Usage:
    python scripts/generate-index.py --apk-dir repo/apk --output-dir repo --inspector-json output.json
"""

import os
import sys
import json
import shutil
import zipfile
import re
import argparse
import subprocess
from pathlib import Path


def find_aapt():
    """Find aapt or aapt2 from PATH or ANDROID_HOME."""
    aapt_cmd = shutil.which("aapt")
    if aapt_cmd:
        return aapt_cmd

    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home:
        build_tools = Path(android_home) / "build-tools"
        if build_tools.is_dir():
            # Get latest version directory
            versions = sorted(build_tools.iterdir(), reverse=True)
            for v in versions:
                cand = v / ("aapt.exe" if os.name == "nt" else "aapt")
                if cand.is_file():
                    return str(cand)
    return None


def extract_metadata_aapt(aapt_path, apk_path):
    """Extract metadata using aapt dump badging."""
    cmd = [aapt_path, "dump", "--include-meta-data", "badging", str(apk_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None

    output = result.stdout
    meta = {}

    # Package info: package: name='...' versionCode='...' versionName='...'
    pkg_match = re.search(r"package:\s+name='([^']+)'\s+versionCode='([^']+)'\s+versionName='([^']+)'", output)
    if pkg_match:
        meta["pkg"] = pkg_match.group(1)
        meta["code"] = int(pkg_match.group(2))
        meta["version"] = pkg_match.group(3)

    # Label: application-label:'...' or application: label='...'
    label_match = re.search(r"application-label(?:-[a-zA-Z]+)?:\s*'([^']+)'", output)
    if not label_match:
        label_match = re.search(r"application:\s+label='([^']+)'", output)
    if label_match:
        name = label_match.group(1)
        # Strip prefix "Tachiyomi: " if present
        if name.startswith("Tachiyomi: "):
            name = name[len("Tachiyomi: "):]
        meta["name"] = name

    # NSFW meta-data
    nsfw_match = re.search(r"meta-data:\s+name='tachiyomi\.extension\.nsfw'\s+value='([^']+)'", output)
    if nsfw_match:
        meta["nsfw"] = int(nsfw_match.group(1))
    else:
        meta["nsfw"] = 0

    # Extension class
    class_match = re.search(r"meta-data:\s+name='tachiyomi\.extension\.class'\s+value='([^']+)'", output)
    if class_match:
        meta["class"] = class_match.group(1)

    # Icon path in APK: application-icon-640:'...' or application-icon-320:'...' or icon='...'
    icon_matches = re.findall(r"application-icon-\d+:\s*'([^']+)'", output)
    if icon_matches:
        meta["icon_path"] = icon_matches[-1]
    else:
        fallback_icon = re.search(r"application:\s+.*icon='([^']+)'", output)
        if fallback_icon:
            meta["icon_path"] = fallback_icon.group(1)

    return meta


def extract_metadata_fallback(apk_path):
    """Fallback metadata extractor using zipfile inspection and filename convention."""
    filename = apk_path.name
    # Filename format: tachiyomi-{lang}.{name}-v{version}.apk
    match = re.match(r"^tachiyomi-([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_\-]+)-v([0-9\.]+)\.apk$", filename)
    meta = {}
    if match:
        meta["lang"] = match.group(1)
        ext_slug = match.group(2)
        meta["version"] = match.group(3)
        parts = meta["version"].split(".")
        meta["code"] = int(parts[-1]) if parts[-1].isdigit() else 1
        meta["name"] = ext_slug.capitalize()
        meta["pkg"] = f"eu.kanade.tachiyomi.extension.{meta['lang']}.{ext_slug}"
    else:
        meta["name"] = apk_path.stem
        meta["pkg"] = f"eu.kanade.tachiyomi.extension.{apk_path.stem}"
        meta["code"] = 1
        meta["version"] = "1.4.1"
        meta["lang"] = "en"

    meta["nsfw"] = 0
    return meta


def extract_icon(apk_path, icon_in_apk, output_icon_path):
    """Extract an icon file from the APK."""
    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            if icon_in_apk and icon_in_apk in z.namelist():
                with open(output_icon_path, "wb") as out:
                    out.write(z.read(icon_in_apk))
                return True
            # Search for best mipmap icon
            candidates = [n for n in z.namelist() if "ic_launcher" in n and n.endswith(".png")]
            if candidates:
                # Prefer xxxhdpi or xxhdpi
                candidates.sort(key=lambda x: ("xxxhdpi" in x, "xxhdpi" in x, "xhdpi" in x), reverse=True)
                with open(output_icon_path, "wb") as out:
                    out.write(z.read(candidates[0]))
                return True
    except Exception as e:
        print(f"Warning: Failed to extract icon from {apk_path.name}: {e}", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate legacy Tachiyomi extension repository indexes")
    parser.add_argument("--apk-dir", default="repo/apk", help="Directory where APKs are located")
    parser.add_argument("--output-dir", default="repo", help="Output directory for index.json and index.min.json")
    parser.add_argument("--icon-dir", default="repo/icon", help="Directory where icons should be saved")
    parser.add_argument("--inspector-json", default="", help="Path to output.json from Inspector.jar")
    parser.add_argument("--repo-name", default="03DxD12 Legacy Tachiyomi Extensions", help="Repo display name")
    parser.add_argument("--repo-short-name", default="03DxD12", help="Repo short name")
    parser.add_argument("--repo-website", default="https://github.com/03DxD12/tachiyomi-extensions", help="Repo website")
    parser.add_argument("--signing-fingerprint", default="", help="Signing key SHA-256 fingerprint")

    args = parser.parse_args()

    apk_dir = Path(args.apk_dir)
    output_dir = Path(args.output_dir)
    icon_dir = Path(args.icon_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)

    if not apk_dir.exists():
        print(f"Error: APK directory '{apk_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    apk_files = sorted(apk_dir.glob("*.apk"))
    if not apk_files:
        print(f"Warning: No .apk files found in '{apk_dir}'.", file=sys.stderr)

    # Load Inspector JSON if provided
    inspector_data = {}
    if args.inspector_json and os.path.isfile(args.inspector_json):
        try:
            with open(args.inspector_json, "r", encoding="utf-8") as f:
                inspector_data = json.load(f)
            print(f"Loaded inspector data for {len(inspector_data)} packages from {args.inspector_json}")
        except Exception as e:
            print(f"Warning: Failed to read inspector JSON: {e}", file=sys.stderr)

    aapt_path = find_aapt()
    if aapt_path:
        print(f"Using aapt at: {aapt_path}")
    else:
        print("Notice: aapt not found in PATH or ANDROID_HOME. Using fallback metadata extraction.")

    extensions = []

    for apk in apk_files:
        meta = None
        if aapt_path:
            meta = extract_metadata_aapt(aapt_path, apk)

        if not meta:
            meta = extract_metadata_fallback(apk)

        pkg_name = meta.get("pkg")
        if not pkg_name:
            print(f"Skipping {apk.name}: Could not determine package name.")
            continue

        # Determine language from APK filename (tachiyomi-{lang}.{name}-v...) or package
        lang_match = re.search(r"^tachiyomi-([a-zA-Z0-9_\-]+)\.", apk.name)
        lang = lang_match.group(1) if lang_match else "en"

        # Extract icon
        icon_path = icon_dir / f"{pkg_name}.png"
        extract_icon(apk, meta.get("icon_path"), icon_path)

        # Sources determination
        sources = []
        if pkg_name in inspector_data:
            sources = inspector_data[pkg_name]
            # If single source, adjust lang if needed
            if len(sources) == 1 and "lang" in sources[0]:
                src_lang = sources[0]["lang"]
                if src_lang not in ("all", "other") and lang not in ("all", "other"):
                    lang = src_lang
        else:
            # Fallback source entry
            source_id = str(abs(hash(meta["name"])) % (10**18))
            sources.append({
                "name": meta["name"],
                "lang": lang,
                "id": source_id,
                "baseUrl": "",
                "versionId": 1,
                "hasCloudflare": 0
            })

        entry = {
            "name": meta["name"],
            "pkg": pkg_name,
            "apk": apk.name,
            "lang": lang,
            "code": meta.get("code", 1),
            "version": meta.get("version", "1.4.1"),
            "nsfw": meta.get("nsfw", 0),
            "sources": sources
        }
        extensions.append(entry)
        print(f"Indexed: {entry['name']} ({entry['pkg']}) v{entry['version']} [lang: {entry['lang']}]")

    # Sort extensions by name
    extensions.sort(key=lambda x: (x["lang"] != "en", x["name"].lower()))

    # Write index.json (pretty)
    index_json_path = output_dir / "index.json"
    with open(index_json_path, "w", encoding="utf-8") as f:
        json.dump(extensions, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Generated: {index_json_path} ({len(extensions)} extensions)")

    # Write index.min.json (minified)
    index_min_json_path = output_dir / "index.min.json"
    with open(index_min_json_path, "w", encoding="utf-8") as f:
        json.dump(extensions, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Generated: {index_min_json_path}")

    # Write repo.json (metadata)
    repo_json_path = output_dir / "repo.json"
    repo_data = {
        "meta": {
            "name": args.repo_name,
            "shortName": args.repo_short_name,
            "website": args.repo_website,
            "signingKeyFingerprint": args.signing_fingerprint
        }
    }
    with open(repo_json_path, "w", encoding="utf-8") as f:
        json.dump(repo_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Generated: {repo_json_path}")

    # Write README.md in repo directory
    repo_readme_path = output_dir / "README.md"
    readme_content = f"""# 03DxD12 Legacy Tachiyomi Extension Repository

This repository provides manga extensions compatible with legacy **Tachiyomi** (v0.15.2+, v0.14.x) and compatible forks that require the `index.min.json` repository index format.

## Repository URL

To add this repository to your Tachiyomi app:

```text
https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.min.json
```

### How to Add:
1. Open **Tachiyomi**.
2. Go to **More** -> **Settings** -> **Browse** -> **Extension repos**.
3. Tap **Add repository** (+).
4. Paste the URL:
   `https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.min.json`
5. Tap **Add**.
6. Go back to the **Browse** -> **Extensions** tab and pull down to refresh.

---

### Available Extensions ({len(extensions)})

| Name | Package | Language | Version | NSFW |
|---|---|---|---|---|
"""
    for ext in extensions:
        nsfw_tag = "🔞 Yes" if ext["nsfw"] == 1 else "No"
        readme_content += f"| {ext['name']} | `{ext['pkg']}` | {ext['lang']} | {ext['version']} | {nsfw_tag} |\n"

    with open(repo_readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"Generated: {repo_readme_path}")


if __name__ == "__main__":
    main()
