# Synthetic API response examples

These hand-authored JSON files are frontend integration fixtures for Guardian API contract v1.1 (OpenAPI 3.1), updated for v1.2 with the optional additional_actions and finding signal fields. The unchanged v1.1 copies are in the [archive](../archive/README.md). They are not measured model outputs, live customer records or evidence that the business endpoints are implemented.

| File | Schema | Use |
| --- | --- | --- |
| [analysis-dossier.json](analysis-dossier.json) | Analysis | Customer-safe source-linked fee contradiction with an explicitly refund-linked message |
| [investigation-dossier.json](investigation-dossier.json) | Investigation | Ops trace example using initial root context, exact lookup and access events, then final synthesis within three model requests |

UUIDs, organizations, times, messages and financial context are synthetic. Match real generated IDs from a sandbox when integrating the backend. Do not hard-code these findings as runtime AI decisions. A source binding does not prove semantic correctness or partner culpability. See [API examples](../api-examples.md), [AI design](../ai-investigation.md) and [evaluation](../evaluation.md).
