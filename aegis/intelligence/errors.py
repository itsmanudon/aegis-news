"""Task failure means no AnalysisResult is produced."""


class IntelligenceError(RuntimeError):
    pass


class NoPredictions(IntelligenceError):
    """Valid inference with no findings; frozen analyses require a nonempty output."""


class InvalidPrediction(IntelligenceError):
    pass


class ModelUnavailable(IntelligenceError):
    pass


class UnsupportedLanguage(IntelligenceError):
    pass
