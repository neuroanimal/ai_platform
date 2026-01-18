"""
Anomaly & Risk Detection Algorithms - Minimal API wrappers
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False

@dataclass
class AnomalyResult:
    anomaly_scores: np.ndarray
    anomalies: np.ndarray
    threshold: Optional[float] = None

@dataclass
class ChangePointResult:
    change_points: np.ndarray
    scores: Optional[np.ndarray] = None

class AnomalyDetection:
    """Minimal wrappers for anomaly and risk detection algorithms"""
    
    def isolation_forest(self, data: np.ndarray, contamination: float = 0.1, **kwargs) -> AnomalyResult:
        """Isolation Forest anomaly detection"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = IsolationForest(contamination=contamination, **kwargs)
        anomaly_labels = model.fit_predict(data)
        anomaly_scores = model.decision_function(data)
        
        anomalies = np.where(anomaly_labels == -1)[0]
        
        return AnomalyResult(
            anomaly_scores=anomaly_scores,
            anomalies=anomalies,
            threshold=np.percentile(anomaly_scores, contamination * 100)
        )
    
    def one_class_svm(self, data: np.ndarray, nu: float = 0.1, kernel: str = 'rbf', **kwargs) -> AnomalyResult:
        """One-Class SVM anomaly detection"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = OneClassSVM(nu=nu, kernel=kernel, **kwargs)
        anomaly_labels = model.fit_predict(data)
        anomaly_scores = model.decision_function(data)
        
        anomalies = np.where(anomaly_labels == -1)[0]
        
        return AnomalyResult(
            anomaly_scores=anomaly_scores,
            anomalies=anomalies,
            threshold=0.0
        )
    
    def spc_control_chart(self, data: np.ndarray, window_size: int = 30, 
                         sigma_level: float = 3.0) -> AnomalyResult:
        """Statistical Process Control (SPC) anomaly detection"""
        
        # Calculate rolling statistics
        rolling_mean = np.convolve(data, np.ones(window_size)/window_size, mode='valid')
        rolling_std = np.array([np.std(data[max(0, i-window_size):i+1]) 
                               for i in range(len(data))])
        
        # Pad rolling_mean to match data length
        rolling_mean = np.concatenate([np.full(window_size-1, rolling_mean[0]), rolling_mean])
        
        # Calculate control limits
        ucl = rolling_mean + sigma_level * rolling_std
        lcl = rolling_mean - sigma_level * rolling_std
        
        # Detect anomalies
        anomalies = np.where((data > ucl) | (data < lcl))[0]
        
        # Calculate anomaly scores (distance from control limits)
        upper_violations = np.maximum(0, data - ucl)
        lower_violations = np.maximum(0, lcl - data)
        anomaly_scores = upper_violations + lower_violations
        
        return AnomalyResult(
            anomaly_scores=anomaly_scores,
            anomalies=anomalies,
            threshold=0.0
        )
    
    def bayesian_changepoint(self, data: np.ndarray, model: str = "rbf", 
                           min_size: int = 2, **kwargs) -> ChangePointResult:
        """Bayesian change point detection"""
        if not RUPTURES_AVAILABLE:
            raise ImportError("ruptures required for change point detection")
        
        # Choose detection algorithm
        if model == "rbf":
            algo = rpt.Pelt(model="rbf", min_size=min_size, **kwargs)
        elif model == "normal":
            algo = rpt.Pelt(model="normal", min_size=min_size, **kwargs)
        else:
            algo = rpt.Pelt(model=model, min_size=min_size, **kwargs)
        
        algo.fit(data)
        change_points = algo.predict(pen=10)
        
        # Remove the last point (end of series)
        if change_points and change_points[-1] == len(data):
            change_points = change_points[:-1]
        
        return ChangePointResult(
            change_points=np.array(change_points)
        )
    
    def statistical_anomaly(self, data: np.ndarray, method: str = "zscore", 
                          threshold: float = 3.0) -> AnomalyResult:
        """Statistical anomaly detection (Z-score, Modified Z-score, IQR)"""
        
        if method == "zscore":
            mean = np.mean(data)
            std = np.std(data)
            anomaly_scores = np.abs((data - mean) / std)
            anomalies = np.where(anomaly_scores > threshold)[0]
            
        elif method == "modified_zscore":
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            anomaly_scores = 0.6745 * (data - median) / mad
            anomalies = np.where(np.abs(anomaly_scores) > threshold)[0]
            
        elif method == "iqr":
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            anomaly_scores = np.maximum(lower_bound - data, data - upper_bound)
            anomaly_scores = np.maximum(anomaly_scores, 0)
            anomalies = np.where((data < lower_bound) | (data > upper_bound))[0]
            
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return AnomalyResult(
            anomaly_scores=anomaly_scores,
            anomalies=anomalies,
            threshold=threshold
        )
    
    def ensemble_anomaly(self, data: np.ndarray, methods: list = None) -> AnomalyResult:
        """Ensemble anomaly detection combining multiple methods"""
        
        if methods is None:
            methods = ['isolation_forest', 'one_class_svm', 'statistical']
        
        all_scores = []
        all_anomalies = []
        
        for method in methods:
            try:
                if method == 'isolation_forest':
                    result = self.isolation_forest(data)
                elif method == 'one_class_svm':
                    result = self.one_class_svm(data)
                elif method == 'statistical':
                    result = self.statistical_anomaly(data)
                elif method == 'spc':
                    result = self.spc_control_chart(data)
                else:
                    continue
                
                # Normalize scores to [0, 1]
                normalized_scores = (result.anomaly_scores - result.anomaly_scores.min()) / \
                                  (result.anomaly_scores.max() - result.anomaly_scores.min() + 1e-8)
                
                all_scores.append(normalized_scores)
                all_anomalies.append(result.anomalies)
                
            except ImportError:
                continue
        
        if not all_scores:
            raise RuntimeError("No anomaly detection methods available")
        
        # Ensemble scoring (average)
        ensemble_scores = np.mean(all_scores, axis=0)
        
        # Ensemble anomalies (majority vote)
        anomaly_votes = np.zeros(len(data))
        for anomalies in all_anomalies:
            anomaly_votes[anomalies] += 1
        
        # Consider as anomaly if majority of methods agree
        threshold_votes = len(methods) / 2
        ensemble_anomalies = np.where(anomaly_votes > threshold_votes)[0]
        
        return AnomalyResult(
            anomaly_scores=ensemble_scores,
            anomalies=ensemble_anomalies,
            threshold=np.percentile(ensemble_scores, 90)
        )