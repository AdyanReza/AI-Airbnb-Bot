from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from typing import Dict, Any
import json
import logging
from ..config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    """User model for storing user information and preferences"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    preferences = Column(String)  # JSON string of preferences
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    feedback = relationship("ListingFeedback", back_populates="user")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences as dictionary"""
        try:
            return json.loads(self.preferences) if self.preferences else {}
        except Exception as e:
            logger.error(f"Error parsing preferences for user {self.telegram_id}: {e}")
            return {}
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """Update user preferences"""
        try:
            current_prefs = self.get_preferences()
            current_prefs.update(preferences)
            self.preferences = json.dumps(current_prefs)
            self.last_active = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error updating preferences for user {self.telegram_id}: {e}")

class ListingFeedback(Base):
    """Model for storing user feedback on listings"""
    __tablename__ = 'listing_feedback'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    listing_id = Column(String)
    liked = Column(Boolean)
    feedback_text = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Features at time of feedback
    price = Column(Float, default=0.0)
    bedrooms = Column(Integer, default=0)
    bathrooms = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    cleanliness_score = Column(Float, default=0.0)
    value_score = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    
    @classmethod
    def from_listing(cls, listing: Dict[str, Any], user_id: int, liked: bool):
        """Create feedback instance from listing data"""
        try:
            return cls(
                user_id=user_id,
                listing_id=listing['id'],
                liked=liked,
                price=float(listing.get('price', 0)),
                bedrooms=int(listing.get('bedrooms', 0)),
                bathrooms=int(listing.get('bathrooms', 0)),
                rating=float(listing.get('rating', 0)),
                location_score=float(listing.get('location_score', 0)),
                cleanliness_score=float(listing.get('cleanliness_score', 0)),
                value_score=float(listing.get('value_score', 0))
            )
        except Exception as e:
            logger.error(f"Error creating feedback from listing: {e}")
            return None

def init_db():
    """Initialize database and create tables"""
    engine = create_engine(Config.DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
