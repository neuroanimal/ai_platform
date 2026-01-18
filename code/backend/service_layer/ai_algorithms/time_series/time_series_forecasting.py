"""
Time Series Forecasting Algorithms - Minimal API wrappers
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

@dataclass
class ForecastResult:
    predictions: np.ndarray
    confidence_intervals: Optional[np.ndarray] = None
    model_params: Optional[Dict] = None

class TimeSeriesForecasting:
    """Minimal wrappers for time series forecasting algorithms"""
    
    def prophet(self, data: pd.DataFrame, periods: int = 30, **kwargs) -> ForecastResult:
        """Facebook Prophet forecasting"""
        if not PROPHET_AVAILABLE:
            raise ImportError("prophet required")
        
        # Ensure proper column names
        if 'ds' not in data.columns or 'y' not in data.columns:
            data = data.copy()
            data.columns = ['ds', 'y']
        
        model = Prophet(**kwargs)
        model.fit(data)
        
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        
        return ForecastResult(
            predictions=forecast['yhat'].values,
            confidence_intervals=np.column_stack([forecast['yhat_lower'].values, forecast['yhat_upper'].values])
        )
    
    def arima(self, data: np.ndarray, order: Tuple[int, int, int] = (1, 1, 1), steps: int = 30) -> ForecastResult:
        """ARIMA forecasting"""
        if not STATSMODELS_AVAILABLE:
            raise ImportError("statsmodels required")
        
        model = ARIMA(data, order=order)
        fitted = model.fit()
        
        forecast = fitted.forecast(steps=steps)
        conf_int = fitted.get_forecast(steps=steps).conf_int()
        
        return ForecastResult(
            predictions=forecast,
            confidence_intervals=conf_int.values,
            model_params={'aic': fitted.aic, 'bic': fitted.bic}
        )
    
    def sarima(self, data: np.ndarray, order: Tuple[int, int, int] = (1, 1, 1), 
               seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12), steps: int = 30) -> ForecastResult:
        """SARIMA forecasting"""
        if not STATSMODELS_AVAILABLE:
            raise ImportError("statsmodels required")
        
        model = SARIMAX(data, order=order, seasonal_order=seasonal_order)
        fitted = model.fit(disp=False)
        
        forecast = fitted.forecast(steps=steps)
        conf_int = fitted.get_forecast(steps=steps).conf_int()
        
        return ForecastResult(
            predictions=forecast,
            confidence_intervals=conf_int.values,
            model_params={'aic': fitted.aic, 'bic': fitted.bic}
        )
    
    def lstm(self, data: np.ndarray, lookback: int = 60, steps: int = 30, epochs: int = 50) -> ForecastResult:
        """LSTM forecasting"""
        if not TF_AVAILABLE:
            raise ImportError("tensorflow required")
        
        # Prepare data
        X, y = self._prepare_lstm_data(data, lookback)
        
        # Build model
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(lookback, 1)),
            tf.keras.layers.LSTM(50),
            tf.keras.layers.Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        model.fit(X, y, epochs=epochs, verbose=0)
        
        # Generate predictions
        last_sequence = data[-lookback:].reshape(1, lookback, 1)
        predictions = []
        
        for _ in range(steps):
            pred = model.predict(last_sequence, verbose=0)[0, 0]
            predictions.append(pred)
            
            # Update sequence
            last_sequence = np.roll(last_sequence, -1, axis=1)
            last_sequence[0, -1, 0] = pred
        
        return ForecastResult(predictions=np.array(predictions))
    
    def temporal_transformer(self, data: np.ndarray, seq_len: int = 60, steps: int = 30, 
                           d_model: int = 64, epochs: int = 50) -> ForecastResult:
        """Temporal Transformer forecasting"""
        if not TF_AVAILABLE:
            raise ImportError("tensorflow required")
        
        # Prepare data
        X, y = self._prepare_lstm_data(data, seq_len)
        
        # Build transformer model
        inputs = tf.keras.layers.Input(shape=(seq_len, 1))
        
        # Multi-head attention
        attention = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=d_model)(inputs, inputs)
        attention = tf.keras.layers.Dropout(0.1)(attention)
        attention = tf.keras.layers.LayerNormalization()(inputs + attention)
        
        # Feed forward
        ff = tf.keras.layers.Dense(d_model, activation='relu')(attention)
        ff = tf.keras.layers.Dense(1)(ff)
        ff = tf.keras.layers.Dropout(0.1)(ff)
        outputs = tf.keras.layers.LayerNormalization()(attention + ff)
        
        # Final prediction
        outputs = tf.keras.layers.GlobalAveragePooling1D()(outputs)
        outputs = tf.keras.layers.Dense(1)(outputs)
        
        model = tf.keras.Model(inputs, outputs)
        model.compile(optimizer='adam', loss='mse')
        model.fit(X, y, epochs=epochs, verbose=0)
        
        # Generate predictions
        last_sequence = data[-seq_len:].reshape(1, seq_len, 1)
        predictions = []
        
        for _ in range(steps):
            pred = model.predict(last_sequence, verbose=0)[0, 0]
            predictions.append(pred)
            
            # Update sequence
            last_sequence = np.roll(last_sequence, -1, axis=1)
            last_sequence[0, -1, 0] = pred
        
        return ForecastResult(predictions=np.array(predictions))
    
    def _prepare_lstm_data(self, data: np.ndarray, lookback: int) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for LSTM training"""
        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i])
        return np.array(X).reshape(-1, lookback, 1), np.array(y)