from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, LeaveOneOut
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import numpy as np
import logging

logger = logging.getLogger(__name__)
class DrugModel:
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=5,
            min_samples_split=2,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.target_weights = {}
        
    def set_target_weights(self, target_weights):
        """Set target weights from STRING confidence scores"""
        self.target_weights = target_weights
        
    def train(self, X, y):
        """Train model with target weight awareness"""
        # Log-transform IC50 values
        # y = np.log10(y)

        y = np.log10(y + 1e-6) 
        
        if len(X) <= 5:
            logger.warning(f"Very few samples: {len(X)}. Using Leave-One-Out validation.")
            cv = LeaveOneOut()
        elif len(X) <= 20:
            logger.warning(f"Limited samples: {len(X)}. Reducing cross-validation splits.")
            cv = 3
        else:
            cv = 5
            

        if len(X) == 1:
            logger.warning("Only one sample available. Skipping cross-validation.")
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            print("\nModel Performance:")
            print("- Cannot calculate performance metrics with single sample")
            return
            
        # Train/val split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scaling features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Cross-validation
        try:
            cv_scores = cross_val_score(
                self.model, X_train_scaled, y_train,
                cv=cv, scoring='neg_mean_absolute_error'
            )
            logger.info(f"CV MAE: {-cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")
            
        # Final training
        self.model.fit(X_train_scaled, y_train)
        
        # Validation
        predictions = self.model.predict(X_val_scaled)
        mae = mean_absolute_error(y_val, predictions)
        r2 = r2_score(y_val, predictions)
        
        print(f"\nMulti-Target Model Performance:")
        print(f"- Samples Used: {len(X)}")
        print(f"- Validation MAE: {mae:.3f} log units")
        print(f"- R² Score: {r2:.3f}")
        print(f"- Number of targets: {len(self.target_weights)}")
        
    def predict(self, X, target=None):
        X_scaled = self.scaler.transform(X)
        base_predictions = np.power(10, self.model.predict(X_scaled))
        
        # If target is specified, adjust prediction based on target weight
        if target and target in self.target_weights:
            weight = self.target_weights[target]
            #higher weight = lower IC50
            return base_predictions * (1 / max(weight, 0.1))
        
        return base_predictions
