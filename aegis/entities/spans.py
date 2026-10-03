"""Document-aware span validation beyond the frozen records' local constraints."""


def span_matches(text: str, surface: str, start: int, end: int) -> bool:
    return 0 <= start < end <= len(text) and text[start:end] == surface
