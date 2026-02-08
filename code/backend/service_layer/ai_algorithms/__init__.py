"""
AI Algorithms - Comprehensive collection of AI algorithm wrappers
"""
from .unsupervised import UnsupervisedLearning, ClusterResult, DimensionReductionResult
from .time_series import TimeSeriesForecasting, ForecastResult
from .anomaly_detection import AnomalyDetection, AnomalyResult, ChangePointResult
from .explainable_ai import ExplainableAI, ExplanationResult, RuleResult, CausalResult
from .computer_vision import ComputerVision, FilterResult, FeatureResult, FlowResult

__all__ = [
    # Unsupervised Learning
    'UnsupervisedLearning',
    'ClusterResult',
    'DimensionReductionResult',

    # Time Series
    'TimeSeriesForecasting',
    'ForecastResult',

    # Anomaly Detection
    'AnomalyDetection',
    'AnomalyResult',
    'ChangePointResult',

    # Explainable AI
    'ExplainableAI',
    'ExplanationResult',
    'RuleResult',
    'CausalResult',

    # Computer Vision
    'ComputerVision',
    'FilterResult',
    'FeatureResult',
    'FlowResult'
]