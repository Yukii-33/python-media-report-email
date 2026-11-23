import argparse
import sys
from pathlib import Path

# Make the repository root importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.report_delivery import StreamingUser, deliver_report, email_from_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and deliver one media report")
    parser.add_argument("email")
    parser.add_argument("--name", default="Creator")
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()
    result = deliver_report(
        StreamingUser(args.email, args.name, args.minutes), args.output, email_from_environment()
    )
    print(f"created {result.report_path} and sent message {result.message_id}")


if __name__ == "__main__":
    main()
