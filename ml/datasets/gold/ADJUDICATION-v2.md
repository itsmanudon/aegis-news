# Gold v2 adjudication record

Review date: 2026-10-03. Single agent semantic review completed before new inference.
**Independent human sign-off is still pending.** This is not a claim of human-reviewed ground truth.
Original CC0 v1 remains untouched. No rules, thresholds, weights or taxonomy were tuned.

Two decisions change two samples: Metro Council topic becomes `politics.policy`;
City Museum becomes event `general` with no typed event extraction, because an exhibition
opening is not a company product launch. This reduces event sentences from 13 to 12.

Offsets use half-open Python character positions in the original text. All 17 exact
spans/types and supplied-candidate resolution targets remain unchanged. JSON records
preserve original/adjudicated fields, per-field changed flags and full rationales.

| # | Actor / exact span | Topic | Sentiment | Event | Changed? | Review rationale / ambiguity |
|---|---|---|---|---|---|---|
| 1 | Atlas Labs [0,10) | business.earnings | positive | company.earnings | no | Named lab reports financial results; exact organization span and sole supplied candidate are coherent. Strong profit growth is positive. None identified within this short synthetic statement. |
| 2 | Meridian Works [0,14) | business.earnings | positive | company.earnings | no | Quarterly revenue surplus is a financial-results report even without the literal earnings keyword; costs improved is positive. Revenue surplus is nonstandard financial phrasing; retain broad earnings interpretation, not a keyword-driven label. |
| 3 | Delta Bank [0,10) | economy | neutral | economy.rate_change | no | Named bank acts institutionally. Rate hike as inflation rose has no stated beneficiary or adverse outcome; neutral is retained. Rate hikes may help savers or harm borrowers; no target-specific sentiment is asserted. |
| 4 | Reserve Council [0,15) | economy | positive | economy.rate_change | no | Council acts as an institution. Reduced borrowing costs describes a rate change and a beneficial stated direction. Support is a policy intention, not demonstrated economic success; neutral is also defensible. |
| 5 | Pixel Forge [0,11) | technology.ai | positive | company.product_launch | no | Named software developer launches an AI product. Improved reliability provides explicit positive valence. No independent evidence validates the reliability claim; annotate the reported statement only. |
| 6 | Orion Systems [0,13), IBM [69,72) | technology.ai | mixed | company.product_launch | no | Orion Systems and IBM are organizations at exact spans. Product launch follows failure, so mixed is retained. IBM has no supplied candidate and remains unresolved. Launch is not proof of success; mixed reflects recovery/launch plus an explicit failed trial. Supporting an existing launch is not a second launch event. |
| 7 | River Parliament [0,16) | politics.policy | neutral | policy.change | no | Parliament acts institutionally. Legislation changes policy with no stated valence. Policy effects are unspecified. |
| 8 | Metro Council [0,13) | politics.policy | positive | policy.change | yes | Adoption of a water-protection policy is the same primary policy subject as legislation; use politics.policy consistently. Two identical council candidates require abstention. politics/public-policy is an overlapping canonical label; choose the policy-specific label by subject, not model keywords. Protection is intent; neutral sentiment is defensible. |
| 9 | Harbor Council [0,14) | regional | positive | general | no | Council is an institutional actor. Library opening is a community benefit under the retained annotation policy, but no existing event subtype represents it. Positive valence is inferred from a new public service; neutral is defensible. Event taxonomy lacks civic-service opening. |
| 10 | Cedar District [0,14) | regional | mixed | general | no | District acts institutionally and the fixture supplies an organization candidate. Repair plus storm damage supports mixed sentiment. Cedar District can denote a location or governing institution; organization is retained from its agency/candidate context. Taxonomy lacks road repair/disaster recovery. |
| 11 | Copper Basin [0,12) | commodities | negative | commodity.supply_disruption | no | Copper Basin is a reporting actor with an organization candidate. Closure/outage is adverse and fits supply disruption. Name can denote a geographic basin or operator; retain institutional reading, flag type ambiguity rather than force geographic certainty. |
| 12 | Wheat Cooperative [0,17) | commodities | negative | commodity.supply_disruption | no | Cooperative is an organization; halted deliveries after floods is adverse supply disruption even without trigger keywords. Taxonomy does not separately represent flooding; retain the stated delivery-disruption event. |
| 13 | Secure Harbor [0,13) | technology | negative | security.cyber_incident | no | Named organization reports ransomware/data breach; adverse cyber incident and technology topic are coherent. No claim is made about real organizations or actual incidents. |
| 14 | Beacon Network [0,14) | technology | mixed | security.cyber_incident | no | Named network restores service following a harmful cyberattack; mixed outcome and cyber incident are explicit. Network can denote infrastructure or operator; institutional agency supports organization. Restoration does not erase harm. |
| 15 | City Museum [0,11) | regional | neutral | general | yes | Museum is an institution. A cultural exhibit opening is not evidence of a company product launch: use general and no typed extracted event. Regional is the closest existing primary-subject label. Canonical taxonomy has no culture/exhibition event or topic. Technology is exhibit content, not necessarily the primary news beat; regional/general are both plausible. Report the representability gap. |
| 16 | Valley Gallery [0,14) | regional | positive | general | no | Gallery is an institution; improved access is positive. Regional/general labels retain the cultural/local-news interpretation. Taxonomy lacks culture/exhibition opening. Actual sentiment toward the artwork is not specified. |

Resolution: exact supplied fictional candidate matches retained; IBM stays unresolved
because no candidate is provided; Metro Council stays unresolved because two equally named
candidates are provided. This tests abstention/candidate coverage, not global entity linking.

Retrieval relevance remains the original one-partner-per-category judgment. It is coarse
and incomplete: civic libraries and galleries may be useful neighbors without being the
annotated partner. No relevance labels were changed after viewing embeddings.

Gold v2 is evaluation-only for this comparison: no training, fine-tuning or threshold
selection. The original set was already seen during development, so gold v2 is not an
independent held-out corpus. Have a human domain reviewer sign off and collect a separate
licensed real-news held-out set before making broader quality claims.
