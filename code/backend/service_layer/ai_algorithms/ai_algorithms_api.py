"""
Unified AI Algorithms API - Single entry point for all AI algorithms
"""
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np
import pandas as pd

from .unsupervised import UnsupervisedLearning
from .time_series import TimeSeriesForecasting
from .anomaly_detection import AnomalyDetection
from .explainable_ai import ExplainableAI
from .computer_vision import ComputerVision

class AIAlgorithmsAPI:
    """Unified API for all AI algorithms with minimal interface"""
    
    def __init__(self):
        self.unsupervised = UnsupervisedLearning()
        self.time_series = TimeSeriesForecasting()
        self.anomaly = AnomalyDetection()
        self.explainable = ExplainableAI()
        self.vision = ComputerVision()
    
    # Unsupervised Learning shortcuts
    def cluster(self, data: np.ndarray, method: str = 'kmeans', **kwargs):
        """Unified clustering interface"""
        if method == 'kmeans':
            return self.unsupervised.kmeans(data, **kwargs)
        elif method == 'dbscan':
            return self.unsupervised.dbscan(data, **kwargs)
        elif method == 'hierarchical':
            return self.unsupervised.hierarchical(data, **kwargs)
        else:
            raise ValueError(f"Unknown clustering method: {method}")
    
    def reduce_dimensions(self, data: np.ndarray, method: str = 'pca', **kwargs):
        """Unified dimensionality reduction interface"""
        if method == 'pca':
            return self.unsupervised.pca(data, **kwargs)
        elif method == 'ica':
            return self.unsupervised.ica(data, **kwargs)
        elif method == 'autoencoder':
            return self.unsupervised.autoencoder(data, **kwargs)
        else:
            raise ValueError(f"Unknown reduction method: {method}")
    
    # Time Series shortcuts
    def forecast(self, data: Union[np.ndarray, pd.DataFrame], method: str = 'prophet', **kwargs):
        """Unified forecasting interface"""
        if method == 'prophet':
            return self.time_series.prophet(data, **kwargs)
        elif method == 'arima':
            return self.time_series.arima(data, **kwargs)
        elif method == 'sarima':
            return self.time_series.sarima(data, **kwargs)
        elif method == 'lstm':
            return self.time_series.lstm(data, **kwargs)
        elif method == 'transformer':
            return self.time_series.temporal_transformer(data, **kwargs)
        else:
            raise ValueError(f"Unknown forecasting method: {method}")
    
    # Anomaly Detection shortcuts
    def detect_anomalies(self, data: np.ndarray, method: str = 'isolation_forest', **kwargs):
        """Unified anomaly detection interface"""
        if method == 'isolation_forest':
            return self.anomaly.isolation_forest(data, **kwargs)
        elif method == 'one_class_svm':
            return self.anomaly.one_class_svm(data, **kwargs)
        elif method == 'spc':
            return self.anomaly.spc_control_chart(data, **kwargs)
        elif method == 'statistical':
            return self.anomaly.statistical_anomaly(data, **kwargs)
        elif method == 'ensemble':
            return self.anomaly.ensemble_anomaly(data, **kwargs)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")
    
    def detect_changepoints(self, data: np.ndarray, **kwargs):
        """Change point detection"""
        return self.anomaly.bayesian_changepoint(data, **kwargs)
    
    # Explainable AI shortcuts
    def explain_model(self, model, X_train: np.ndarray, X_test: np.ndarray, 
                     method: str = 'shap', **kwargs):
        """Unified model explanation interface"""
        if method == 'shap':
            return self.explainable.shap_explanation(model, X_train, X_test, **kwargs)
        elif method == 'lime':
            return self.explainable.lime_explanation(model, X_train, X_test, **kwargs)
        elif method == 'attribution':
            return self.explainable.feature_attribution(model, X_test, **kwargs)
        else:
            raise ValueError(f"Unknown explanation method: {method}")
    
    def extract_rules(self, X: np.ndarray, y: np.ndarray, method: str = 'tree', **kwargs):
        """Extract interpretable rules"""
        if method == 'tree':
            return self.explainable.extract_tree_rules(X, y, **kwargs)
        elif method == 'forest':
            return self.explainable.extract_forest_rules(X, y, **kwargs)
        else:
            raise ValueError(f"Unknown rule extraction method: {method}")
    
    def discover_causality(self, data: np.ndarray, feature_names: List[str], 
                          method: str = 'pc', **kwargs):
        """Causal discovery"""
        if method == 'pc':
            return self.explainable.causal_discovery_pc(data, feature_names, **kwargs)
        elif method == 'scm':
            causal_structure = kwargs.get('causal_structure', [])
            return self.explainable.build_scm(data, feature_names, causal_structure)
        elif method == 'dag':
            adjacency_matrix = kwargs.get('adjacency_matrix')
            return self.explainable.build_dag(adjacency_matrix, feature_names)
        else:
            raise ValueError(f"Unknown causal discovery method: {method}")
    
    # Computer Vision shortcuts
    def apply_filter(self, image: np.ndarray, filter_type: str = 'sobel', **kwargs):
        """Unified image filtering interface"""
        if filter_type == 'sobel':
            return self.vision.sobel_filter(image, **kwargs)
        elif filter_type == 'canny':
            return self.vision.canny_edge(image, **kwargs)
        elif filter_type == 'gaussian':
            return self.vision.gaussian_blur(image, **kwargs)
        elif filter_type == 'median':
            return self.vision.median_filter(image, **kwargs)
        elif filter_type.startswith('morph_'):
            operation = filter_type.replace('morph_', '')
            return self.vision.morphological_operations(image, operation, **kwargs)
        else:
            raise ValueError(f"Unknown filter type: {filter_type}")
    
    def extract_features(self, image: np.ndarray, method: str = 'hog', **kwargs):
        """Unified feature extraction interface"""
        if method == 'hog':
            return self.vision.hog_features(image, **kwargs)
        elif method == 'sift':
            return self.vision.sift_features(image, **kwargs)
        elif method == 'surf':
            return self.vision.surf_features(image, **kwargs)
        elif method == 'corners':
            return self.vision.corner_detection(image, **kwargs)
        else:
            raise ValueError(f"Unknown feature extraction method: {method}")
    
    def optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray, **kwargs):
        """Optical flow calculation"""
        return self.vision.lucas_kanade_flow(prev_frame, curr_frame, **kwargs)
    
    # Utility methods
    def get_available_methods(self) -> Dict[str, List[str]]:
        """Get all available methods for each category"""
        return {
            'clustering': ['kmeans', 'dbscan', 'hierarchical'],
            'dimensionality_reduction': ['pca', 'ica', 'autoencoder'],
            'forecasting': ['prophet', 'arima', 'sarima', 'lstm', 'transformer'],
            'anomaly_detection': ['isolation_forest', 'one_class_svm', 'spc', 'statistical', 'ensemble'],
            'explanation': ['shap', 'lime', 'attribution'],
            'rule_extraction': ['tree', 'forest'],
            'causal_discovery': ['pc', 'scm', 'dag'],
            'image_filters': ['sobel', 'canny', 'gaussian', 'median', 'morph_opening', 'morph_closing'],
            'feature_extraction': ['hog', 'sift', 'surf', 'corners'],
            'optical_flow': ['lucas_kanade']
        }
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check which dependencies are available"""
        dependencies = {}
        
        try:
            import sklearn
            dependencies['sklearn'] = True
        except ImportError:
            dependencies['sklearn'] = False
        
        try:
            import tensorflow
            dependencies['tensorflow'] = True
        except ImportError:
            dependencies['tensorflow'] = False
        
        try:
            import cv2
            dependencies['opencv'] = True
        except ImportError:
            dependencies['opencv'] = False
        
        try:
            import skimage
            dependencies['skimage'] = True
        except ImportError:
            dependencies['skimage'] = False
        
        try:
            import prophet
            dependencies['prophet'] = True
        except ImportError:
            dependencies['prophet'] = False
        
        try:
            import statsmodels
            dependencies['statsmodels'] = True
        except ImportError:
            dependencies['statsmodels'] = False
        
        try:
            import shap
            dependencies['shap'] = True
        except ImportError:
            dependencies['shap'] = False
        
        try:
            import lime
            dependencies['lime'] = True
        except ImportError:
            dependencies['lime'] = False
        
        return dependencies