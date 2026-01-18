"""
Explainable AI & Governance Algorithms - Minimal API wrappers
"""
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    import lime
    from lime.lime_tabular import LimeTabularExplainer
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

try:
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import networkx as nx
    import pgmpy
    from pgmpy.models import BayesianNetwork
    from pgmpy.estimators import PC
    CAUSAL_AVAILABLE = True
except ImportError:
    CAUSAL_AVAILABLE = False

@dataclass
class ExplanationResult:
    feature_importance: np.ndarray
    feature_names: Optional[List[str]] = None
    explanation_data: Optional[Dict] = None

@dataclass
class RuleResult:
    rules: List[str]
    rule_importance: Optional[np.ndarray] = None

@dataclass
class CausalResult:
    graph: Any
    edges: List[Tuple[str, str]]
    causal_effects: Optional[Dict] = None

class ExplainableAI:
    """Minimal wrappers for explainable AI and governance algorithms"""
    
    def shap_explanation(self, model, X_train: np.ndarray, X_test: np.ndarray, 
                        feature_names: Optional[List[str]] = None) -> ExplanationResult:
        """SHAP (SHapley Additive exPlanations) model explanation"""
        if not SHAP_AVAILABLE:
            raise ImportError("shap required")
        
        # Choose appropriate explainer
        try:
            explainer = shap.TreeExplainer(model)
        except:
            try:
                explainer = shap.LinearExplainer(model, X_train)
            except:
                explainer = shap.KernelExplainer(model.predict, X_train[:100])
        
        shap_values = explainer.shap_values(X_test)
        
        # Handle multi-class case
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        
        # Calculate feature importance
        feature_importance = np.mean(np.abs(shap_values), axis=0)
        
        return ExplanationResult(
            feature_importance=feature_importance,
            feature_names=feature_names,
            explanation_data={'shap_values': shap_values}
        )
    
    def lime_explanation(self, model, X_train: np.ndarray, X_test: np.ndarray,
                        feature_names: Optional[List[str]] = None, mode: str = 'classification') -> ExplanationResult:
        """LIME (Local Interpretable Model-agnostic Explanations)"""
        if not LIME_AVAILABLE:
            raise ImportError("lime required")
        
        explainer = LimeTabularExplainer(
            X_train,
            feature_names=feature_names,
            mode=mode
        )
        
        # Explain first instance
        explanation = explainer.explain_instance(
            X_test[0], 
            model.predict_proba if mode == 'classification' else model.predict,
            num_features=len(feature_names) if feature_names else X_test.shape[1]
        )
        
        # Extract feature importance
        feature_importance = np.zeros(X_test.shape[1])
        for idx, importance in explanation.as_list():
            if isinstance(idx, str) and feature_names:
                idx = feature_names.index(idx)
            feature_importance[idx] = importance
        
        return ExplanationResult(
            feature_importance=feature_importance,
            feature_names=feature_names,
            explanation_data={'lime_explanation': explanation}
        )
    
    def extract_tree_rules(self, X: np.ndarray, y: np.ndarray, 
                          feature_names: Optional[List[str]] = None, max_depth: int = 5) -> RuleResult:
        """Extract rules from decision tree"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        # Train decision tree
        tree = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
        tree.fit(X, y)
        
        # Extract rules as text
        tree_rules = export_text(tree, feature_names=feature_names)
        
        # Parse rules into list
        rules = []
        for line in tree_rules.split('\n'):
            line = line.strip()
            if line and not line.startswith('|') and 'class:' in line:
                rules.append(line)
        
        # Calculate rule importance (feature importance from tree)
        rule_importance = tree.feature_importances_
        
        return RuleResult(
            rules=rules,
            rule_importance=rule_importance
        )
    
    def extract_forest_rules(self, X: np.ndarray, y: np.ndarray,
                           feature_names: Optional[List[str]] = None, n_estimators: int = 10) -> RuleResult:
        """Extract rules from random forest"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")
        
        # Train random forest
        forest = RandomForestClassifier(n_estimators=n_estimators, max_depth=5, random_state=42)
        forest.fit(X, y)
        
        # Extract rules from each tree
        all_rules = []
        for i, tree in enumerate(forest.estimators_):
            tree_rules = export_text(tree, feature_names=feature_names)
            for line in tree_rules.split('\n'):
                line = line.strip()
                if line and not line.startswith('|') and 'class:' in line:
                    all_rules.append(f"Tree_{i}: {line}")
        
        return RuleResult(
            rules=all_rules,
            rule_importance=forest.feature_importances_
        )
    
    def causal_discovery_pc(self, data: np.ndarray, feature_names: List[str], 
                           alpha: float = 0.05) -> CausalResult:
        """PC algorithm for causal discovery"""
        if not CAUSAL_AVAILABLE:
            raise ImportError("pgmpy and networkx required")
        
        import pandas as pd
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=feature_names)
        
        # Apply PC algorithm
        pc = PC(data=df)
        estimated_model = pc.estimate(significance_level=alpha)
        
        # Extract edges
        edges = list(estimated_model.edges())
        
        return CausalResult(
            graph=estimated_model,
            edges=edges
        )
    
    def build_scm(self, data: np.ndarray, feature_names: List[str], 
                  causal_structure: List[Tuple[str, str]]) -> CausalResult:
        """Build Structural Causal Model (SCM)"""
        if not CAUSAL_AVAILABLE:
            raise ImportError("pgmpy required")
        
        # Create Bayesian Network with given structure
        model = BayesianNetwork(causal_structure)
        
        # Estimate parameters (simplified)
        import pandas as pd
        df = pd.DataFrame(data, columns=feature_names)
        
        # Calculate simple causal effects (correlation-based approximation)
        causal_effects = {}
        for parent, child in causal_structure:
            if parent in df.columns and child in df.columns:
                correlation = df[parent].corr(df[child])
                causal_effects[f"{parent} -> {child}"] = correlation
        
        return CausalResult(
            graph=model,
            edges=causal_structure,
            causal_effects=causal_effects
        )
    
    def build_dag(self, adjacency_matrix: np.ndarray, feature_names: List[str]) -> CausalResult:
        """Build Directed Acyclic Graph (DAG)"""
        if not CAUSAL_AVAILABLE:
            raise ImportError("networkx required")
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes
        G.add_nodes_from(feature_names)
        
        # Add edges based on adjacency matrix
        edges = []
        for i, parent in enumerate(feature_names):
            for j, child in enumerate(feature_names):
                if adjacency_matrix[i, j] > 0:
                    G.add_edge(parent, child, weight=adjacency_matrix[i, j])
                    edges.append((parent, child))
        
        # Check if DAG is acyclic
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Graph contains cycles - not a valid DAG")
        
        return CausalResult(
            graph=G,
            edges=edges
        )
    
    def feature_attribution(self, model, X: np.ndarray, baseline: Optional[np.ndarray] = None,
                           method: str = 'integrated_gradients') -> ExplanationResult:
        """Feature attribution using various methods"""
        
        if method == 'integrated_gradients':
            return self._integrated_gradients(model, X, baseline)
        elif method == 'gradient':
            return self._gradient_attribution(model, X)
        else:
            raise ValueError(f"Unknown attribution method: {method}")
    
    def _integrated_gradients(self, model, X: np.ndarray, baseline: Optional[np.ndarray] = None) -> ExplanationResult:
        """Integrated Gradients attribution (simplified)"""
        if baseline is None:
            baseline = np.zeros_like(X[0])
        
        # Simple approximation of integrated gradients
        steps = 50
        attributions = []
        
        for x in X:
            path_attributions = []
            for alpha in np.linspace(0, 1, steps):
                interpolated = baseline + alpha * (x - baseline)
                
                # Approximate gradient (finite difference)
                epsilon = 1e-5
                grad = np.zeros_like(x)
                
                for i in range(len(x)):
                    x_plus = interpolated.copy()
                    x_minus = interpolated.copy()
                    x_plus[i] += epsilon
                    x_minus[i] -= epsilon
                    
                    try:
                        pred_plus = model.predict([x_plus])[0]
                        pred_minus = model.predict([x_minus])[0]
                        grad[i] = (pred_plus - pred_minus) / (2 * epsilon)
                    except:
                        grad[i] = 0
                
                path_attributions.append(grad)
            
            # Integrate along path
            integrated_grad = np.mean(path_attributions, axis=0)
            attribution = (x - baseline) * integrated_grad
            attributions.append(attribution)
        
        return ExplanationResult(
            feature_importance=np.mean(np.abs(attributions), axis=0)
        )
    
    def _gradient_attribution(self, model, X: np.ndarray) -> ExplanationResult:
        """Simple gradient-based attribution"""
        attributions = []
        epsilon = 1e-5
        
        for x in X:
            grad = np.zeros_like(x)
            
            for i in range(len(x)):
                x_plus = x.copy()
                x_minus = x.copy()
                x_plus[i] += epsilon
                x_minus[i] -= epsilon
                
                try:
                    pred_plus = model.predict([x_plus])[0]
                    pred_minus = model.predict([x_minus])[0]
                    grad[i] = (pred_plus - pred_minus) / (2 * epsilon)
                except:
                    grad[i] = 0
            
            attributions.append(grad)
        
        return ExplanationResult(
            feature_importance=np.mean(np.abs(attributions), axis=0)
        )