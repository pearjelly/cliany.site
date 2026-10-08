# Clean Install Browser Dependency Boundary

**Date:** 2026-10-08 (Asia/Shanghai). **Scope:** maintainer-controlled Python 3.11.14 wheel installation on macOS arm64, without the project lockfile. No live model or candidate promotion is claimed.

## Reproduced failure

The v0.16.375 candidate at `10e50055` declared an unconstrained `browser-use` dependency. Fresh GitHub CI resolved `browser-use==0.11.13` and `mcp==2.3.0`; benchmark, curated-adapter, extraction and full-suite jobs failed during collection with `ModuleNotFoundError: No module named 'pydantic_settings'`. See [CI run 37712890900](https://github.com/pearjelly/cliany.site/actions/runs/37712890900) and [Embodied CI run 37712890839](https://github.com/pearjelly/cliany.site/actions/runs/37712890839).

A wheel built from the same candidate reproduced the failure in a new virtual environment: installation completed, but even `cliany-site --version` exited 1 during browser-use import. This is a CLI startup failure, not only a missing test dependency. The existing development lockfile used browser-use 0.12.4 and passed 3,222 offline tests, so that locked run did not prove fresh-install compatibility.

## Fix and independent install

The package requirement is now `browser-use==0.12.4`, matching the already validated development runtime. The lockfile changed only that requirement's metadata; no locked package versions changed. A newly built wheel was installed into a separate empty virtual environment without `uv.lock`:

```bash
uv build --out-dir /tmp/cliany-v375-dist-fixed-20261008
uv venv --python 3.11 /tmp/cliany-v375-fixed-clean-20261008
uv pip install --python /tmp/cliany-v375-fixed-clean-20261008/bin/python \
  /tmp/cliany-v375-dist-fixed-20261008/cliany_site-0.16.375-py3-none-any.whl
uv pip check --python /tmp/cliany-v375-fixed-clean-20261008/bin/python
CLIANY_QA_OFFLINE=1 /tmp/cliany-v375-fixed-clean-20261008/bin/python \
  tests/embodied/benchmark_cli.py --runtime-home /tmp/cliany-v375-fixed-runtime-20261008 \
  -- --version
CLIANY_QA_OFFLINE=1 /tmp/cliany-v375-fixed-clean-20261008/bin/python \
  tests/embodied/benchmark_cli.py --runtime-home /tmp/cliany-v375-fixed-runtime-20261008 \
  -- --help
```

The install resolved 145 packages, including browser-use 0.12.4, MCP 1.26.0 and pydantic-settings 2.15.0. `uv pip check` reported all installed packages compatible. Both CLI probes exited 0; the version probe reported 0.16.375 and help listed the built-in commands. The existing benchmark runner isolates cliany-site runtime data while preserving the normal OS HOME. Twine accepted the wheel and sdist, and 568 focused project metadata, release documentation and site-content tests passed after the dependency and release-note edits.

## Limits

These probes establish fresh-install resolution and CLI startup on one host. They do not establish a new user's workflow completion, live provider availability or future compatibility of arbitrary upstream packages. The final release still requires ordinary and real-browser CI on its final master SHA, tagged readiness and public distribution checks. Upgrading browser-use from the pinned version requires an explicit compatibility review.
