# Historical archive records

The earlier platform was archived on 18 September 2026 from commit `3078ffb60d58952b4c193b2edb1de7d85375bbab`. These records describe the historical local archive; they do not imply that every archived file is included in this public checkout.

| Record | Scope |
|---|---|
| `legacy_file_inventory.csv` | File paths, byte counts, timestamps and SHA-256 values |
| `legacy_inventory.csv` | Run directories identified by metrics, missions, actions and related marker files |
| `correction_map.csv` | The 20 original and corrected B0 D60 units and their hashes |
| `migration_verification.json` | Historical archive comparison and correction checks |
| `git_metadata_recovery.json` | Recovery of Git metadata after an interrupted local directory move |

The historical archive comparison matched 329,525 files by SHA-256. The run inventory identified 15,385 directories, of which 15,369 contained metrics. The remaining 16 were test, smoke, verification and replay directories. This discovery-based inventory is not a matrix-level completeness check and does not by itself establish missing or complete primary runs.

The 20 corrected B0 D60 units replace the corresponding original observations; they do not increase the number of independent experimental units. The archive checks verify storage integrity, not simulator behavior. External machines, cloud-only files and material already missing at the time were outside their scope.

Some historical manifests contain local archive paths. Those paths identify provenance and are not downloadable data locations. Public ITSAC data are indexed in the [paper supplement](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016/itsac/supplement).
