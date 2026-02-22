# competition/ml/linear_regression.py
import numpy as np
import joblib
import os
from datetime import datetime
from django.conf import settings
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import re

class EssayScorePredictor:
    """
    Linear Regression model to predict essay scores based on various features
    """
    
    def __init__(self, model_path=None):
        self.model = None
        self.scaler = None
        self.feature_names = [
            'word_count', 
            'paragraph_count', 
            'sentence_count',
            'avg_word_length',
            'unique_word_ratio',
            'title_length',
            'has_question',
            'has_numbers'
        ]
        
        # Model paths
        self.models_dir = os.path.join(settings.BASE_DIR, 'competition', 'ml', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        if model_path:
            self.load_model(model_path)
    
    def extract_features(self, essay):
        """
        Extract features from an essay for prediction
        """
        from ..models import Essay
        
        if isinstance(essay, Essay):
            content = essay.content or ""
            title = essay.title or ""
        else:
            content = essay.get('content', '')
            title = essay.get('title', '')
        
        # Basic text metrics
        words = content.split()
        sentences = re.findall(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        # Feature 1: Word count
        word_count = len(words)
        
        # Feature 2: Paragraph count
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Feature 3: Sentence count
        sentence_count = len(sentences)
        
        # Feature 4: Average word length
        avg_word_length = np.mean([len(word) for word in words]) if words else 0
        
        # Feature 5: Unique word ratio (vocabulary richness)
        unique_words = len(set(word.lower() for word in words))
        unique_word_ratio = unique_words / word_count if word_count > 0 else 0
        
        # Feature 6: Title length
        title_length = len(title)
        
        # Feature 7: Has question mark?
        has_question = 1 if '?' in content else 0
        
        # Feature 8: Has numbers?
        has_numbers = 1 if any(char.isdigit() for char in content) else 0
        
        features = np.array([
            word_count,
            paragraph_count,
            sentence_count,
            avg_word_length,
            unique_word_ratio,
            title_length,
            has_question,
            has_numbers
        ])
        
        return features
    
    def prepare_training_data(self, essays=None):
        """
        Prepare training data from evaluated essays
        """
        from ..models import Essay
        
        if essays is None:
            # Get all accepted essays with scores
            essays = Essay.objects.filter(
                status='accepted',
                total_score__gt=0
            ).select_related('competition')
        
        if not essays.exists():
            return None, None
        
        X = []
        y = []
        
        for essay in essays:
            features = self.extract_features(essay)
            X.append(features)
            y.append(essay.total_score)
        
        return np.array(X), np.array(y)
    
    def train(self, essays=None, test_size=0.2, random_state=42):
        """
        Train the linear regression model
        """
        X, y = self.prepare_training_data(essays)
        
        if X is None or len(X) < 5:
            return {
                'success': False,
                'message': f'Not enough training data. Need at least 5 essays, got {len(X) if X is not None else 0}'
            }
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = LinearRegression()
        self.model.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        
        # Feature importance (coefficients)
        feature_importance = {}
        for name, coef in zip(self.feature_names, self.model.coef_):
            feature_importance[name] = float(coef)
        
        # Sort by absolute importance
        feature_importance = dict(
            sorted(
                feature_importance.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
        )
        
        # Normalize importance to percentages
        total_importance = sum(abs(v) for v in feature_importance.values())
        feature_importance_pct = {
            k: (abs(v) / total_importance * 100) if total_importance > 0 else 0
            for k, v in feature_importance.items()
        }
        
        results = {
            'success': True,
            'metrics': {
                'train': {
                    'r2': float(train_r2),
                    'rmse': float(train_rmse),
                    'mae': float(train_mae),
                    'samples': len(y_train)
                },
                'test': {
                    'r2': float(test_r2),
                    'rmse': float(test_rmse),
                    'mae': float(test_mae),
                    'samples': len(y_test)
                }
            },
            'feature_importance': feature_importance_pct,
            'total_samples': len(y)
        }
        
        return results
    
    def save_model(self, name=None):
        """
        Save trained model to disk
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        if name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = f'essay_predictor_{timestamp}'
        
        model_path = os.path.join(self.models_dir, f'{name}.joblib')
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, model_path)
        
        return model_path
    
    def load_model(self, name_or_path):
        """
        Load trained model from disk
        """
        if os.path.exists(name_or_path):
            model_path = name_or_path
        else:
            model_path = os.path.join(self.models_dir, f'{name_or_path}.joblib')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        model_data = joblib.load(model_path)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data.get('feature_names', self.feature_names)
        
        return model_data
    
    def predict(self, essay):
        """
        Predict score for a single essay
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Train the model first.")
        
        features = self.extract_features(essay)
        features_scaled = self.scaler.transform([features])
        
        prediction = self.model.predict(features_scaled)[0]
        
        # Ensure prediction is within 0-100 range
        prediction = max(0, min(100, prediction))
        
        return {
            'predicted_score': float(prediction),
            'features': dict(zip(self.feature_names, features))
        }