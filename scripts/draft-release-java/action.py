import argparse
import re
import git
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Category(Enum):
    FEAT = "Features"
    FIX = "Bugfixes"
    CHORE = "Chores"
    MISC = "Misc"


@dataclass
class ParsedCommit:
    sha: str
    short_sha: str
    message: str


CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(?P<verb>\w+)(\((?P<scope>[\w-]+)\))?(?P<breaking>!)?: (?P<message>.*)$",
    re.IGNORECASE,
)

def generate_changelog(output: Path, repository_url: str):
    repository = git.Repo(search_parent_directories=True)
    since = max(repository.tags, default=None, key=lambda tag: tag.commit.committed_date)
    query = f"{since}..HEAD" if since else "HEAD"

    # Group commits by category and project
    builder: dict[Category, dict[str, list[ParsedCommit]]] = {
        cat: defaultdict(list) for cat in Category
    }

    commits = repository.iter_commits(query)
    for commit in commits:
        if not commit.parents:
            continue

        matched = CONVENTIONAL_COMMIT_REGEX.match(str(commit.summary))
        category = Category.MISC
        project = ""
        message: str

        if matched:
            message = str(matched.group("message"))
            match matched.group("verb"):
                case "feat": category = Category.FEAT
                case "fix": category = Category.FIX
                case "chore": category = Category.CHORE
                case _: category = Category.MISC
            if matched.group("scope"):
                project = str(matched.group("scope"))
        else:
            message = commit.summary

        builder[category][project].append(
            ParsedCommit(sha=commit.hexsha, short_sha=repository.git.rev_parse(commit.hexsha, short=7),message=message))

    with open(output, "w") as f:
        for category in Category:
            projects = builder[category]
            if not projects:
                continue
            f.writelines(f"### {category.value}\n\n")
            for project in sorted(projects.keys()):
                commits = projects[project]
                if project:
                    f.writelines(f"#### {project}\n\n")
                f.writelines([f" - [`{c.short_sha}`]({repository_url}/commit/{c.sha}) {c.message}\n" for c in commits])
                f.writelines("\n")
            f.writelines("\n")

    print("It is done!")

def main():
    parser = argparse.ArgumentParser(description="Generate changelog from git commits")
    parser.add_argument("--repository_url", type=str, required=True)
    parser.add_argument("--output", type=Path, default=Path("CHANGELOG.md"))
    args = parser.parse_args()
    generate_changelog(output=args.output, repository_url=args.repository_url)

if __name__ == "__main__":
    main()
