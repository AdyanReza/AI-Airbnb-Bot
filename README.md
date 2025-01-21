# Airbnb AI Recommendation Bot 

An intelligent Telegram bot that helps you find the perfect Airbnb accommodation while learning from your preferences. The bot uses machine learning to understand your taste and provide increasingly personalized recommendations.

##  Key Features

### AI-Powered Recommendations
- **Personalized Learning**: The bot learns from every interaction and adapts its recommendations to your preferences
- **Smart Feedback System**: Like or dislike listings to help the bot understand your taste
- **Preference Analysis**: Get insights into your preferred price ranges, room configurations, and amenities
- **Continuous Improvement**: The more you interact, the better the recommendations become

### Search Capabilities
- Location-based search
- Date range selection
- Guest count specification
- Amenity preferences (WiFi, Kitchen, Pool, etc.)
- Price range filtering

### Analytics & Insights
- View your interaction statistics
- See your learned preferences
- Track the bot's learning progress
- Analyze your booking patterns

##  Getting Started

1. **Start the Bot**
   - Search for `@your_bot_username` on Telegram
   - Click "Start" or send `/start`

2. **Basic Commands**
   ```
   /start    - Begin using the bot
   /search   - Start a new accommodation search
   /stats    - View your personalized statistics and preferences
   /help     - Show available commands
   ```

3. **Searching for Accommodations**
   1. Type `/search` to begin
   2. Enter your destination
   3. Select check-in and check-out dates
   4. Specify number of guests
   5. Choose desired amenities
   6. Set your price range

4. **Training the AI**
   - For each listing shown:
     -  Click "Like" for properties you're interested in
     -  Click "Dislike" for properties that don't match your taste
   - The bot learns from each interaction to improve future recommendations

5. **Tracking Learning Progress**
   - Use `/stats` to see:
     - Your interaction history
     - Price preferences learned
     - Preferred room configurations
     - Rating patterns
     - Overall learning progress

##  How the AI Learning Works

The bot employs a sophisticated learning system that:

1. **Collects Feedback**
   - Tracks which properties you like/dislike
   - Analyzes common features among preferred listings
   - Identifies patterns in your choices

2. **Analyzes Preferences**
   - Price ranges you tend to prefer
   - Typical room configurations you like
   - Preferred amenities
   - Location patterns
   - Rating thresholds

3. **Adapts Recommendations**
   - Adjusts search rankings based on your history
   - Prioritizes listings matching your preferences
   - Provides increasingly personalized suggestions

4. **Measures Progress**
   - Shows learning progress percentage
   - Provides detailed preference insights
   - Offers transparent feedback analysis

##  Tips for Best Results

1. **Provide Regular Feedback**
   - Like or dislike each listing you see
   - The more feedback you provide, the better the recommendations

2. **Check Your Stats**
   - Use `/stats` regularly to understand how the bot learns
   - Review your preference profile to ensure it matches your taste

3. **Vary Your Searches**
   - Try different locations and property types
   - This helps the bot understand your preferences in various contexts

##  Technical Requirements

- Python 3.8+
- Required packages:
  ```
  python-telegram-bot==20.7
  SQLAlchemy==1.4.23
  scikit-learn==0.24.2
  python-dotenv==0.19.0
  ```

##  Privacy

- All user data is securely stored and used only for improving recommendations
- No personal information is shared with third parties
- Feedback data is used exclusively for personalization


