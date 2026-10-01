"""Build a maintained adapter archive without touching installed user adapters."""

import argparse
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from cliany_site.config import ClanySiteConfig
from cliany_site.marketplace import pack_adapter, validate_adapter_domain

SOURCES = Path(__file__).resolve().parents[1] / "curated_adapters"


def build(domain: str, version: str, output_dir: Path) -> Path:
    validate_adapter_domain(domain)
    if not version or "/" in version or "\\" in version:
        raise ValueError("version must be a nonempty filename-safe value")
    source = SOURCES / domain
    if not source.is_dir():
        raise FileNotFoundError(f"maintained adapter source not found: {domain}")
    output = output_dir / f"{domain}-{version}.cliany-adapter.tar.gz"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    with tempfile.TemporaryDirectory(prefix="cliany-curated-adapter-") as temporary:
        home = Path(temporary)
        adapter_dir = home / "adapters" / domain
        shutil.copytree(source, adapter_dir)
        with patch("cliany_site.marketplace.get_config", return_value=ClanySiteConfig(home_dir=home)):
            package = pack_adapter(domain, version=version, author="cliany.site")
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.domain, args.version, args.output_dir))


if __name__ == "__main__":
    main()
