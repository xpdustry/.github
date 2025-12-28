import argparse
import re
import json
from pathlib import Path


SEMVER_REGEX = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(-(?P<modifier>[a-zA-Z][0-9a-zA-Z]*)\.(?P<build>0|[1-9]\d*))?$")


def increment_version(version_file: Path, version_file_kind: str) -> bool:
    match version_file_kind:
        case "mindustry-mod":
            with open(version_file, "r") as f:
                content = f.read()
                data = json.loads(content)
                try:
                    old_version = str(data["version"])
                except Exception as e:
                    print("Unable to extract old version from version file: ", e)
                    return False

            parsed = SEMVER_REGEX.match(old_version)
            if not parsed:
                print("Invalid version: ", old_version)
                return False

            major = parsed.group("major")
            minor = parsed.group("minor")
            patch = parsed.group("patch")
            modifier = parsed.group("modifier")
            build = parsed.group("build")

            if modifier:
                # Increment build number if there's a modifier (e.g., v1.0.0-alpha.1)
                new_build = int(build) + 1
                new_version = f"{major}.{minor}.{patch}-{modifier}.{new_build}"
            else:
                # Increment patch number for standard versions (e.g., v1.0.0)
                new_patch = int(patch) + 1
                new_version = f"{major}.{minor}.{new_patch}"

            new_content = content.replace(f'"{old_version}"', f'"{new_version}"')

            with open(version_file, "w") as f:
                f.write(new_content)

            print(f"Version incremented: {old_version} -> {new_version}")
            return True
        case _:
            print("Unknown input kind: ", version_file_kind)
            return False

def main():
    parser = argparse.ArgumentParser(description="Increment version number")
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--version-file-kind", type=str, required=True)
    args = parser.parse_args()
    if not increment_version(
            version_file=args.version_file,
            version_file_kind=args.version_file_kind):
        exit(1)

if __name__ == "__main__":
    main()
