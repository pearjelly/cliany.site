"""Build the maintained ASF Confluence adapter without touching user adapters."""

import argparse
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from cliany_site.config import ClanySiteConfig
from cliany_site.marketplace import pack_adapter

DOMAIN = "cwiki.apache.org"
SOURCE = Path(__file__).resolve().parents[1] / "curated_adapters" / DOMAIN


def build(version: str, output_dir: Path) -> Path:
    if not version or "/" in version or "\\" in version:
        raise ValueError("version must be a nonempty filename-safe value")
    output = output_dir / f"{DOMAIN}-{version}.cliany-adapter.tar.gz"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    with tempfile.TemporaryDirectory(prefix="cliany-curated-confluence-") as temporary:
        home = Path(temporary)
        adapter_dir = home / "adapters" / DOMAIN
        shutil.copytree(SOURCE, adapter_dir)
        with patch("cliany_site.marketplace.get_config", return_value=ClanySiteConfig(home_dir=home)):
            package = pack_adapter(DOMAIN, version=version, author="cliany.site")
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.version, args.output_dir))


if __name__ == "__main__":
    main()
