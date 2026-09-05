# Third-Party Notices

This file identifies external material and services referenced by the repository. It is not a licence grant and does not replace review of the applicable source terms. The repository's Apache-2.0 licence applies only to original material the repository owner has authority to license.

## Data And Metadata Sources

- Clean Energy Regulator (CER): project-register facts, project-page identities, and CEA boundary identities are referenced for provenance. Complete CER responses and the CEA archive remain in ignored local run packages and are not included in the tracked repository.
- Curated CER snapshots under `data/cer/` restate selected EOP101132 registry facts and the public ACCU/SMC distinction with source URLs and access dates. They are not relicensed by Apache-2.0 and do not imply CER endorsement.
- Copernicus Sentinel-2: product identifiers, acquisition metadata, and derived observations originate from Sentinel-2 L2A products and remain subject to the applicable Copernicus data terms.
- Microsoft Planetary Computer: STAC metadata and temporary asset-signing services were used by controlled runs. Microsoft does not endorse this repository, and its service and dataset terms continue to apply.

The reviewed example under `examples/eop101132-v3-abstained/` contains redacted, text-based derivatives including source identifiers, canonical asset URLs, metadata-derived fields, hashes, and run summaries. It contains no raster imagery, CEA archive, raw HTTP payload, signed URL, access credential, or complete current run package.

## Software Dependencies And Services

Runtime and development dependencies are declared in `pyproject.toml` and resolved in `uv.lock`. They are referenced packages, not vendored source code, and each remains under its own licence. The principal direct dependencies are `jsonschema`, `pytest`, `PyYAML`, `numpy`, and `rasterio`.

GitHub Actions workflows may reference `actions/checkout` and `actions/setup-python` at pinned commits. Those actions remain externally maintained works under their respective licences.

## Repository Material

No third-party fonts, photographs, logos, raster images, shapefiles, archives, or copied website templates are tracked. Repository-specific Python, schemas, registries, tests, and original documentation are covered by Apache-2.0 only to the extent that they are original, owner-controlled material. The top-level licence must not be interpreted as relicensing external data, metadata, source responses, derived artifacts, services, dependencies, or third-party marks.

See `docs/DATA_AND_ARTIFACT_LICENSING.md` for the release inventory and remaining public-release decisions.
