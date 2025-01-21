import numpy as np
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MinMaxScaler
import joblib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class RecommendationModel:
    """
    Machine Learning model for Airbnb listing recommendations.
    Uses Naive Bayes for initial recommendations and incorporates user feedback
    for continuous learning.
    """
    
    def __init__(self):
        self.model = MultinomialNB()
        self.scaler = MinMaxScaler()
        self.feature_names = [
            'price', 'bedrooms', 'bathrooms', 'rating',
            'location_score', 'cleanliness_score', 'value_score'
        ]
        
    def _preprocess_features(self, listing_data: Dict) -> np.ndarray:
        """
        Preprocess listing data into format suitable for ML model.
        
        Args:
            listing_data: Dictionary containing listing features
            
        Returns:
            Preprocessed feature array
        """
        features = np.zeros(len(self.feature_names))
        for i, feature in enumerate(self.feature_names):
            features[i] = listing_data.get(feature, 0)
        
        # Scale features to [0,1] range
        return self.scaler.fit_transform(features.reshape(1, -1))
    
    def train(self, training_data: List[Dict], labels: List[int]) -> None:
        """
        Train the recommendation model on historical data.
        
        Args:
            training_data: List of listing dictionaries
            labels: List of binary labels (1 for liked, 0 for disliked)
        """
        try:
            X = np.vstack([self._preprocess_features(item) for item in training_data])
            self.model.fit(X, labels)
            logger.info("Model training completed successfully")
        except Exception as e:
            logger.error(f"Error during model training: {str(e)}")
            raise
    
    def get_recommendations(self, 
                          user_preferences: Dict,
                          available_listings: List[Dict],
                          n_recommendations: int = 5) -> List[Dict]:
        """
        Get personalized recommendations based on user preferences.
        
        Args:
            user_preferences: Dictionary of user preferences
            available_listings: List of available Airbnb listings
            n_recommendations: Number of recommendations to return
            
        Returns:
            List of recommended listings sorted by relevance
        """
        try:
            # Preprocess all listings
            X = np.vstack([self._preprocess_features(listing) 
                          for listing in available_listings])
            
            # Get probability scores for each listing
            scores = self.model.predict_proba(X)[:, 1]  # Probability of class 1 (like)
            
            # Sort listings by score and return top n
            top_indices = np.argsort(scores)[-n_recommendations:][::-1]
            
            recommendations = [
                {**available_listings[i], 'relevance_score': float(scores[i])}
                for i in top_indices
            ]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def update_from_feedback(self, listing_data: Dict, liked: bool) -> None:
        """
        Update model based on user feedback.
        
        Args:
            listing_data: Dictionary containing listing features
            liked: Boolean indicating if user liked the listing
        """
        try:
            X = self._preprocess_features(listing_data)
            y = np.array([1 if liked else 0])
            
            # Partial fit to update the model
            self.model.partial_fit(X, y, classes=np.array([0, 1]))
            logger.info("Model updated with user feedback")
        except Exception as e:
            logger.error(f"Error updating model with feedback: {str(e)}")
            
    def save_model(self, path: str) -> None:
        """Save model to disk"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }, path)
        
    def load_model(self, path: str) -> None:
        """Load model from disk"""
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']
