# ADR-007: Canonical entity vs external asset mapping

Status: Accepted for foundation

## Context

The same organization may have exchange symbols, ISINs and external provider identifiers, while downstream financial systems own assets.

## Decision

Keep canonical Entity identity separate from AssetMapping; venue is required for exchange symbols.

## Consequences

No prices, portfolios, PnL, recommendations or trading signals in AegisNews. Consumer-specific mappings and time validity can be expanded when supported by evidence.
