# Local intelligence

Independent providers implement the frozen ports; `build_engine("light" | "full" | "offline")`
composes them. See [model setup and integration](../../ml/models/README.md) and
[evaluation](../../ml/evaluation/README.md).

## Topic taxonomy v1

Broad labels are business, markets, technology, politics/public-policy, regional, company,
commodities, economy and general. The initial hierarchy also contains business.earnings,
business.mergers, markets.equities, technology.ai and politics.policy. Politics labels describe
subjects; no ideological scores, rankings or recommendations are produced.

## Event taxonomy v1

- company.earnings
- company.acquisition
- company.executive_change
- company.product_launch
- regulatory.action
- policy.change
- economy.rate_change
- commodity.supply_disruption
- security.cyber_incident

`general` is an existing-event classification fallback; it is never emitted as an extracted
event. Extraction proposes sentence-evidenced categories via AnalysisResult → EventExtractionResult.
It does not create canonical NewsEvent facts, infer occurrence dates, or identify participants.
Classification of an existing NewsEvent emits EventClassificationResult with event_id/revision.

Taxonomy labels and baseline lexicons live in `taxonomy.py` and enter configuration hashes.
Provider thresholds, model name/revision/device/token windows are configuration, not scattered
imports. Provider swapping is possible via the existing protocols or the runtime inference port.
