# Marketplace runtime compatibility before installation

**Date:** 2026-11-12 (Asia/Shanghai). **Status:** unpublished correction. Related: [crates.io candidate and verified private archive](https://github.com/pearjelly/cliany.site/pull/134#issuecomment-6817333134).

## Retained installed-package evidence

The actual public PyPI CLI `0.16.398` was given the unchanged private `crates.io-0.1.0` archive, SHA-256 `ad015cca4b20f3b5bf9f0c465ad81097bdb5661074b1e27aea66a7efa1b7f788`. In an empty runtime, `market install --dry-run` returned success without installing. Actual `market install` returned success and wrote the adapter. `verify --strict` then returned `E_VERIFY_STATIC`: the manifest was valid, but the command was `commands_unloadable` due to `ImportError`. No browser action followed. SHA-256 of the retained install envelope: `23f72db5eae0645d439722f67dcc6458577a58114ffa7bcf81f4ec7fa75cc625`; failed strict verify envelope: `45fa7291c6b34a7e6655c380f62c7cc162007d0d0443b5f2ac9747fcaa0bcfb3`. The first observer read the failed verdict at the wrong envelope level; its saved raw outputs, not a retry, establish the result.

## Correction boundary

After integrity and schema validation, parse the package command file without importing it. Compare only direct, top-level named imports from the installed generated-action runtime modules. Unsupported imports now refuse both dry-run and installation before any backup or replacement. The same guard applies to local and remote packages; it does not execute archive code, probe a browser, access a model, or override hash/force policy. Conditional imports and broader runtime behavior still require normal verification.

This does not retrofit public `0.16.398`. Before sharing a pinned candidate archive, publish a supporting CLI, verify that exact public install and archive digest, then repeat fresh installation, strict verification and read-only positive, changed-query and zero replays. Preserve the earlier failed public-package observation and the separate successful private workflow. Do not update candidate status or count maintainers as independent users on these results.
