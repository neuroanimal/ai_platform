"""
Unsupervised Learning Algorithms - Minimal API wrappers
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
    from sklearn.decomposition import PCA, FastICA
    from sklearn.preprocessing import StandardScaler
    import tensorflow as tf
    SKLEARN_AVAILABLE = True
    TF_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    TF_AVAILABLE = False

@dataclass
class ClusterResult:
    labels: np.ndarray
    centers: Optional[np.ndarray] = None
    n_clusters: Optional[int] = None

@dataclass
class DimensionReductionResult:
    transformed_data: np.ndarray
    components: Optional[np.ndarray] = None
    explained_variance: Optional[np.ndarray] = None

class UnsupervisedLearning:
    """Minimal wrappers for unsupervised learning algorithms"""
    
    def __init__(self):
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
    
    def kmeans(self, data: np.ndarray, n_clusters: int = 3, **kwargs) -> ClusterResult:
        """K-means clustering"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = KMeans(n_clusters=n_clusters, **kwargs)
        labels = model.fit_predict(data)
        
        return ClusterResult(
            labels=labels,
            centers=model.cluster_centers_,
            n_clusters=n_clusters
        )
    
    def dbscan(self, data: np.ndarray, eps: float = 0.5, min_samples: int = 5, **kwargs) -> ClusterResult:
        """DBSCAN clustering"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = DBSCAN(eps=eps, min_samples=min_samples, **kwargs)
        labels = model.fit_predict(data)
        
        return ClusterResult(
            labels=labels,
            n_clusters=len(set(labels)) - (1 if -1 in labels else 0)
        )
    
    def hierarchical(self, data: np.ndarray, n_clusters: int = 3, linkage: str = 'ward', **kwargs) -> ClusterResult:
        """Hierarchical clustering"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, **kwargs)
        labels = model.fit_predict(data)
        
        return ClusterResult(
            labels=labels,
            n_clusters=n_clusters
        )
    
    def pca(self, data: np.ndarray, n_components: Optional[int] = None, **kwargs) -> DimensionReductionResult:
        """Principal Component Analysis"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = PCA(n_components=n_components, **kwargs)
        transformed = model.fit_transform(data)
        
        return DimensionReductionResult(
            transformed_data=transformed,
            components=model.components_,
            explained_variance=model.explained_variance_ratio_
        )
    
    def ica(self, data: np.ndarray, n_components: Optional[int] = None, **kwargs) -> DimensionReductionResult:
        """Independent Component Analysis"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        model = FastICA(n_components=n_components, **kwargs)
        transformed = model.fit_transform(data)
        
        return DimensionReductionResult(
            transformed_data=transformed,
            components=model.components_
        )
    
    def autoencoder(self, data: np.ndarray, encoding_dim: int = 32, epochs: int = 50) -> DimensionReductionResult:
        """Simple autoencoder for dimensionality reduction"""
        if not TF_AVAILABLE:
            raise ImportError("tensorflow required")
        
        input_dim = data.shape[1]
        
        # Build autoencoder
        encoder = tf.keras.Sequential([
            tf.keras.layers.Dense(encoding_dim, activation='relu', input_shape=(input_dim,)),
        ])
        
        decoder = tf.keras.Sequential([
            tf.keras.layers.Dense(input_dim, activation='sigmoid', input_shape=(encoding_dim,))
        ])
        
        autoencoder = tf.keras.Sequential([encoder, decoder])
        autoencoder.compile(optimizer='adam', loss='mse')
        
        # Train
        autoencoder.fit(data, data, epochs=epochs, verbose=0)
        
        # Get encoded representation
        encoded = encoder.predict(data, verbose=0)
        
        return DimensionReductionResult(
            transformed_data=encoded
        )