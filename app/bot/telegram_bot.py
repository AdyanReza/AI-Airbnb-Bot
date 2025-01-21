from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    filters
)
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
from ..models.database import User, ListingFeedback, init_db
from ..services.airbnb_scraper import AirbnbAPI
from ..models.recommendation import RecommendationModel
from ..config import Config
import calendar

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get API key from environment variable
AIRBNB_API_KEY = os.getenv('AIRBNB_API_KEY')

# Conversation states
(
    LOCATION,
    SELECT_CHECKIN,
    SELECT_CHECKOUT,
    GUESTS,
    AMENITIES,
    PRICE_RANGE
) = range(6)

class AirbnbBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("No token provided!")
            
        logger.info("Initializing AirbnbBot...")
        self.db = init_db()
        self.scraper = AirbnbAPI(api_key=AIRBNB_API_KEY)
        self.recommendation_model = RecommendationModel()
        
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
        
        # Common amenities and facilities
        self.amenities_options = {
            "wifi": "WiFi 📶",
            "kitchen": "Kitchen 🍳",
            "washer": "Washer 🧺",
            "dryer": "Dryer 👕",
            "ac": "Air Conditioning ❄️",
            "heating": "Heating 🔥",
            "tv": "TV 📺",
            "pool": "Pool 🏊‍♂️",
            "gym": "Gym 💪",
            "parking": "Free Parking 🚗",
            "workspace": "Workspace 💻",
            "pets": "Pets Allowed 🐾"
        }
    
    def _setup_handlers(self):
        """Setup message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("preferences", self.show_preferences))
        self.application.add_handler(CommandHandler("stats", self.stats))  # Add stats handler
        
        # Add feedback handler - IMPORTANT: This must come before the conversation handler
        self.application.add_handler(CallbackQueryHandler(
            self.handle_listing_feedback,
            pattern='^feedback_'
        ))
        
        logger.info("Setting up conversation handler...")
        # Conversation handler for search flow
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('search', self.search_start)],
            states={
                LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.location)],
                SELECT_CHECKIN: [
                    CallbackQueryHandler(self.handle_calendar, pattern='^nav|^cal'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.checkin_fallback)
                ],
                SELECT_CHECKOUT: [
                    CallbackQueryHandler(self.handle_calendar, pattern='^nav|^cal'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.checkout_fallback)
                ],
                GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.guests)],
                AMENITIES: [CallbackQueryHandler(self.amenity_callback)],
                PRICE_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.price_range)]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        self.application.add_handler(conv_handler)
        
        # Add callback query handler for the copy button
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
    async def start(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        user = update.effective_user
        # Create or get user in database
        db_user = self.db.query(User).filter_by(telegram_id=str(user.id)).first()
        if not db_user:
            db_user = User(telegram_id=str(user.id))
            self.db.add(db_user)
            self.db.commit()
            logger.info(f"Created new user in database: {user.id}")
        
        welcome_text = (
            f"👋 Hi {user.first_name}! I'm your Airbnb recommendation assistant.\n\n"
            "I can help you find the perfect place to stay based on your preferences.\n\n"
            "Commands:\n"
            "/search - Start searching for accommodations\n"
            "/stats - View your search statistics and preferences\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(welcome_text)
    
    async def search_start(self, update: Update, context: CallbackContext) -> int:
        """Start the search conversation."""
        await update.message.reply_text(
            "Let's find you a great place to stay! 🏠\n"
            "Where would you like to go?"
        )
        return LOCATION

    async def location(self, update: Update, context: CallbackContext) -> int:
        """Store location and show calendar for dates"""
        context.user_data['location'] = update.message.text
        logger.info(f"Location received: {update.message.text}")
        
        # Create and show calendar for check-in date
        now = datetime.now()
        calendar_markup = self.create_calendar(now.year, now.month)
        await update.message.reply_text(
            "Please select your check-in date:",
            reply_markup=calendar_markup
        )
        return SELECT_CHECKIN

    def create_calendar(self, year: int, month: int, selected_date: datetime = None) -> InlineKeyboardMarkup:
        """Create an inline keyboard with a calendar"""
        # Cache frequently used values
        today = datetime.now()
        current_month = today.month
        current_year = today.year
        
        calendar_keyboard = []
        
        # Add month and year at the top
        month_year = f"{calendar.month_name[month]} {year}"
        calendar_keyboard.append([InlineKeyboardButton(month_year, callback_data="ignore")])
        
        # Add days of week as header
        week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        calendar_keyboard.append(
            [InlineKeyboardButton(day, callback_data="ignore") for day in week_days]
        )
        
        # Pre-calculate month calendar
        cal = calendar.monthcalendar(year, month)
        
        # Get all days in month
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    # Empty day
                    row.append(InlineKeyboardButton(" ", callback_data="ignore"))
                else:
                    # Format the date
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    
                    # Check if date is in the past
                    is_past = (year < current_year or 
                             (year == current_year and month < current_month) or
                             (year == current_year and month == current_month and day < today.day))
                    
                    if is_past:
                        # Past dates are disabled
                        display_day = "✗"
                        callback_data = "ignore"
                    else:
                        # Future or current dates are selectable
                        display_day = f"✓{day}" if selected_date and selected_date.day == day else str(day)
                        callback_data = f"cal_{date_str}"  # Shortened callback data
                        
                    row.append(InlineKeyboardButton(display_day, callback_data=callback_data))
            calendar_keyboard.append(row)
        
        # Add navigation buttons at the bottom
        nav_row = []
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        # Only allow navigation to future months or current month
        can_go_prev = (prev_year > current_year or 
                      (prev_year == current_year and prev_month >= current_month))
        
        if can_go_prev:
            nav_row.append(InlineKeyboardButton("<<", callback_data=f"nav_{prev_year}_{prev_month}"))
        else:
            nav_row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            
        nav_row.append(InlineKeyboardButton(">>", callback_data=f"nav_{next_year}_{next_month}"))
        calendar_keyboard.append(nav_row)
        
        return InlineKeyboardMarkup(calendar_keyboard)

    async def handle_calendar(self, update: Update, context: CallbackContext) -> int:
        """Handle calendar button presses"""
        query = update.callback_query
        await query.answer(cache_time=1)  # Reduced cache time for better responsiveness
        
        if query.data == "ignore":
            return
            
        data = query.data.split('_')
        action = data[0]
        
        try:
            if action == "nav":
                # Quick navigation handling
                year, month = int(data[1]), int(data[2])
                calendar_markup = self.create_calendar(year, month)
                await query.message.edit_reply_markup(reply_markup=calendar_markup)
                return context.user_data.get('calendar_state', SELECT_CHECKIN)
                
            elif action == "cal":
                # Quick date selection handling
                selected_date = datetime.strptime(data[1], "%Y-%m-%d")
                
                if 'checkin_date' not in context.user_data:
                    # Handle check-in date
                    context.user_data['checkin_date'] = selected_date
                    next_day = selected_date + timedelta(days=1)
                    calendar_markup = self.create_calendar(next_day.year, next_day.month)
                    
                    await query.message.edit_text(
                        f"✅ Check-in: {selected_date.strftime('%Y-%m-%d')}\n"
                        f"Select check-out date:",
                        reply_markup=calendar_markup
                    )
                    context.user_data['calendar_state'] = SELECT_CHECKOUT
                    return SELECT_CHECKOUT
                    
                else:
                    # Handle check-out date
                    if selected_date <= context.user_data['checkin_date']:
                        await query.answer("Please select a date after check-in", show_alert=True)
                        return SELECT_CHECKOUT
                        
                    context.user_data['checkout_date'] = selected_date
                    context.user_data['dates'] = f"{context.user_data['checkin_date'].strftime('%Y-%m-%d')} to {selected_date.strftime('%Y-%m-%d')}"
                    
                    await query.message.edit_text(
                        f"✅ Dates selected!\n"
                        f"Check-in: {context.user_data['checkin_date'].strftime('%Y-%m-%d')}\n"
                        f"Check-out: {selected_date.strftime('%Y-%m-%d')}"
                    )
                    
                    await query.message.reply_text("How many guests will be staying?")
                    return GUESTS
                    
        except Exception as e:
            logger.error(f"Calendar error: {e}")
            await query.answer("Error processing selection", show_alert=True)
            return context.user_data.get('calendar_state', SELECT_CHECKIN)

    async def checkin_fallback(self, update: Update, context: CallbackContext) -> int:
        """Fallback for text input instead of calendar for check-in"""
        await update.message.reply_text(
            "Please use the calendar to select your check-in date."
        )
        return SELECT_CHECKIN

    async def checkout_fallback(self, update: Update, context: CallbackContext) -> int:
        """Fallback for text input instead of calendar for check-out"""
        await update.message.reply_text(
            "Please use the calendar to select your check-out date."
        )
        return SELECT_CHECKOUT
    
    async def guests(self, update: Update, context: CallbackContext) -> int:
        """Handle number of guests and ask for amenities preferences."""
        try:
            guests = int(update.message.text)
            if guests < 1 or guests > 16:
                await update.message.reply_text(
                    'Please enter a valid number of guests (1-16)'
                )
                return GUESTS
            
            context.user_data['guests'] = guests
            # Initialize amenities as a set for easier toggling
            context.user_data['selected_amenities'] = set()
            
            # Create amenities keyboard
            keyboard = []
            row = []
            for key, label in self.amenities_options.items():
                if len(row) == 2:  # 2 buttons per row
                    keyboard.append(row)
                    row = []
                row.append(InlineKeyboardButton(
                    f"☐ {label}", 
                    callback_data=f"amenity_{key}_toggle"
                ))
            if row:
                keyboard.append(row)
            
            # Add Done button at the bottom
            keyboard.append([InlineKeyboardButton("✅ Done", callback_data="amenities_done")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "What amenities are important to you? Select all that apply:\n"
                "(Click an option to select/unselect, then click Done when finished)",
                reply_markup=reply_markup
            )
            
            return AMENITIES
            
        except ValueError:
            await update.message.reply_text(
                'Please enter a valid number of guests (e.g., 2)'
            )
            return GUESTS

    async def amenity_callback(self, update: Update, context: CallbackContext) -> int:
        """Handle amenity selection callbacks."""
        query = update.callback_query
        
        # Initialize selected_amenities if not exists
        if 'selected_amenities' not in context.user_data:
            context.user_data['selected_amenities'] = set()
        
        if query.data == "amenities_done":
            # Convert set back to list for JSON serialization
            context.user_data['selected_amenities'] = list(context.user_data['selected_amenities'])
            await query.message.edit_text(
                "Great! Now, what's your price range per night? (format: min-max)\n"
                "Example: 100-200\n"
                "Or just enter a maximum price like: 200"
            )
            return PRICE_RANGE
        
        # Handle amenity toggle
        amenity_data = query.data.split('_')
        if len(amenity_data) == 3:
            amenity_key = amenity_data[1]
            
            # Toggle amenity in set
            if amenity_key in context.user_data['selected_amenities']:
                context.user_data['selected_amenities'].remove(amenity_key)
            else:
                context.user_data['selected_amenities'].add(amenity_key)
            
            # Update keyboard with current selections
            keyboard = []
            row = []
            for key, label in self.amenities_options.items():
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
                is_selected = key in context.user_data['selected_amenities']
                row.append(InlineKeyboardButton(
                    f"{'☑' if is_selected else '☐'} {label}",
                    callback_data=f"amenity_{key}_toggle"
                ))
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("✅ Done", callback_data="amenities_done")])
            
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            # Answer callback to remove loading state
            await query.answer()
            return AMENITIES
        
        await query.answer()
        return AMENITIES

    async def price_range(self, update: Update, context: CallbackContext) -> int:
        """Handle price range and perform the search."""
        try:
            price_text = update.message.text
            if '-' not in price_text:
                try:
                    max_price = int(price_text)
                    min_price = 0
                except ValueError:
                    await update.message.reply_text(
                        'Please enter a valid number or range (e.g., 100-200)'
                    )
                    return PRICE_RANGE
            else:
                try:
                    min_price, max_price = map(int, price_text.split('-'))
                except ValueError:
                    await update.message.reply_text(
                        'Please enter a valid price range (e.g., 100-200)'
                    )
                    return PRICE_RANGE

            search_message = await update.message.reply_text('🔍 Searching for properties...')
            
            # Log search parameters
            logger.info(
                f"Searching with params: location={context.user_data['location']}, "
                f"dates={context.user_data['checkin_date']} to {context.user_data['checkout_date']}, "
                f"guests={context.user_data['guests']}, price={min_price}-{max_price}"
            )
            
            listings = self.scraper.search_listings(
                location=context.user_data['location'],
                check_in=context.user_data['checkin_date'].strftime('%Y-%m-%d'),
                check_out=context.user_data['checkout_date'].strftime('%Y-%m-%d'),
                guests=context.user_data['guests'],
                min_price=min_price,
                max_price=max_price,
                amenities=context.user_data.get('selected_amenities', [])
            )
            
            if not listings:
                await search_message.edit_text(
                    'Sorry, no properties found matching your criteria. 😔\n'
                    'Try adjusting your:\n'
                    '- Price range\n'
                    '- Dates\n'
                    '- Location\n'
                    '- Number of guests\n\n'
                    'Use /search to start a new search.'
                )
                return ConversationHandler.END
            
            await search_message.edit_text(
                f"🏠 Found {len(listings)} properties matching your criteria!\n"
                "Here are the best matches:"
            )
            
            for listing in listings:
                # Store listing in context for feedback handling
                # Generate a unique ID if none exists
                listing_id = listing.get('id', str(hash(f"{listing['url']}_{listing['title']}")))
                context.user_data[f'listing_{listing_id}'] = listing
                
                message = (
                    f"[{listing['title']}]({listing['url']})\n"
                    f"💰 ${listing['price']} per night\n"
                )
                
                if listing.get('rating', 0) > 0:
                    message += f"⭐ {listing['rating']:.1f} ({listing.get('reviews', 0)} reviews)\n"
                
                if listing.get('bedrooms', 0) > 0:
                    message += f"🛏 {listing['bedrooms']} bedroom{'s' if listing['bedrooms'] > 1 else ''}\n"
                
                if listing.get('bathrooms', 0) > 0:
                    message += f"🚿 {listing['bathrooms']} bathroom{'s' if listing['bathrooms'] > 1 else ''}\n"
                
                if listing.get('max_guests', 0) > 0:
                    message += f"👥 Up to {listing['max_guests']} guests\n"
                
                if listing.get('amenities', []):
                    message += f"✨ {', '.join(listing['amenities'][:3])}\n"
                
                message += f"📍 {listing.get('location', 'Location not specified')}"
                
                # Add like/dislike buttons
                keyboard = [
                    [
                        InlineKeyboardButton("👍 Like", callback_data=f"feedback_{listing_id}_like"),
                        InlineKeyboardButton("👎 Dislike", callback_data=f"feedback_{listing_id}_dislike")
                    ]
                ]
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            final_message = (
                f"Those are the best matches I found! 🎉\n\n"
                f"📍 *Location:* {context.user_data['location']}\n"
                f"📅 *Dates:* {context.user_data['checkin_date'].strftime('%Y-%m-%d')} to "
                f"{context.user_data['checkout_date'].strftime('%Y-%m-%d')}\n"
                f"👥 *Guests:* {context.user_data['guests']}\n"
                f"💰 *Price Range:* ${min_price}-{max_price}\n"
            )
            
            if context.user_data.get('selected_amenities'):
                amenities_list = [self.amenities_options[a] for a in context.user_data['selected_amenities']]
                final_message += f"✨ *Amenities:* {', '.join(amenities_list)}\n"
                
            final_message += "\nThe more feedback you provide on listings, the better I can learn your preferences! 🎯"
            
            await update.message.reply_text(final_message, parse_mode='Markdown')
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in price_range handler: {e}", exc_info=True)
            await update.message.reply_text(
                'Sorry, something went wrong. Please try again with a valid price range (e.g., 100-200)'
            )
            return PRICE_RANGE

    async def button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        # Get the search text from context using the short key
        search_text = context.user_data.get('search_texts', {}).get(query.data)
        if search_text:
            await query.message.reply_text(
                f"`{search_text}`\n\n"
                "👆 Copy this text and paste it in Airbnb's search bar",
                parse_mode='Markdown'
            )
    
    async def handle_listing_feedback(self, update: Update, context: CallbackContext) -> None:
        """Handle user feedback on listings"""
        query = update.callback_query
        await query.answer()
        
        # Extract data from callback
        try:
            data = query.data.split('_')  # Format: feedback_listingId_action
            listing_id = data[1]
            action = data[2]  # 'like' or 'dislike'
            
            # Get listing data from context
            listing = context.user_data.get(f'listing_{listing_id}')
            if not listing:
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text("Sorry, I couldn't find this listing's information. Please try searching again.")
                return
            
            # Create feedback entry
            user = self.db.query(User).filter_by(telegram_id=str(update.effective_user.id)).first()
            if not user:
                # Create user if they don't exist
                user = User(telegram_id=str(update.effective_user.id))
                self.db.add(user)
                self.db.commit()
            
            # Create listing feedback object with safe defaults
            feedback_data = {
                'id': listing_id,
                'price': float(listing.get('price', 0)),
                'bedrooms': int(listing.get('bedrooms', 0)),
                'bathrooms': float(listing.get('bathrooms', 0)),
                'rating': float(listing.get('rating', 0)),
                'location_score': float(listing.get('location_score', 0)),
                'cleanliness_score': float(listing.get('cleanliness_score', 0)),
                'value_score': float(listing.get('value_score', 0))
            }
            
            feedback = ListingFeedback.from_listing(feedback_data, user.id, liked=(action == 'like'))
            if feedback:
                self.db.add(feedback)
                self.db.commit()
                
                # Update recommendation model
                self.recommendation_model.update_from_feedback(feedback_data, liked=(action == 'like'))
                
                # Update message to show feedback
                emoji = '👍' if action == 'like' else '👎'
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"You rated {emoji}", callback_data="dummy")
                    ]])
                )
                
                # Show a message about learning
                message = (
                    f"{emoji} Thanks for your feedback! I'll use this to improve your recommendations.\n"
                    f"The more feedback you provide, the better I'll understand your preferences!"
                )
                await query.message.reply_text(message)
            else:
                await query.message.reply_text("Sorry, there was an error processing your feedback.")
            
        except Exception as e:
            logger.error(f"Error handling listing feedback: {e}", exc_info=True)
            await query.message.reply_text("Sorry, there was an error processing your feedback.")

    async def help(self, update: Update, context: CallbackContext):
        """Send a message when the command /help is issued."""
        await update.message.reply_text(
            'Here are the available commands:\n\n'
            '/start - Start the bot\n'
            '/search - Search for Airbnb properties\n'
            '/preferences - View your current preferences\n'
            '/help - Show this help message\n'
            '/cancel - Cancel the current operation'
        )

    async def show_preferences(self, update: Update, context: CallbackContext) -> None:
        """Show user's current preferences and feedback statistics."""
        try:
            user = self.db.query(User).filter_by(telegram_id=str(update.effective_user.id)).first()
            if not user:
                await update.message.reply_text(
                    "I don't have any preferences saved for you yet. "
                    "Use /search to start looking for properties!"
                )
                return

            # Get user's feedback history
            feedback = self.db.query(ListingFeedback).filter_by(user_id=user.id).all()
            liked = sum(1 for f in feedback if f.liked)
            disliked = len(feedback) - liked

            stats_text = (
                "📊 Your Statistics:\n\n"
                f"Total searches: {user.search_count if hasattr(user, 'search_count') else 0}\n"
                f"Listings viewed: {len(feedback)}\n"
                f"Liked: {liked}\n"
                f"Disliked: {disliked}\n"
            )

            await update.message.reply_text(stats_text)

        except Exception as e:
            logger.error(f"Error showing preferences: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, there was an error retrieving your preferences."
            )

    async def stats(self, update: Update, context: CallbackContext):
        """Handle /stats command"""
        try:
            user = self.db.query(User).filter_by(telegram_id=str(update.effective_user.id)).first()
            if not user:
                await update.message.reply_text(
                    "I don't have any statistics for you yet. "
                    "Try searching for some properties first!"
                )
                return

            # Get user's feedback history
            feedback = self.db.query(ListingFeedback).filter_by(user_id=user.id).all()
            liked_listings = [f for f in feedback if f.liked]
            disliked_listings = [f for f in feedback if not f.liked]

            # Basic stats
            message = "📊 *Your Learning Profile*\n\n"
            message += "*Interaction Stats:*\n"
            message += f"🔍 Total searches: {user.search_count if hasattr(user, 'search_count') else 0}\n"
            message += f"👀 Listings viewed: {len(feedback)}\n"
            message += f"👍 Listings liked: {len(liked_listings)}\n"
            message += f"👎 Listings disliked: {len(disliked_listings)}\n\n"

            if liked_listings:
                # Price preferences
                avg_liked_price = sum(f.price for f in liked_listings) / len(liked_listings)
                if disliked_listings:
                    avg_disliked_price = sum(f.price for f in disliked_listings) / len(disliked_listings)
                    price_preference = "lower" if avg_liked_price < avg_disliked_price else "higher"
                    message += "*Price Insights:*\n"
                    message += f"💰 You tend to prefer {price_preference} priced listings\n"
                    message += f"   Avg. liked price: ${avg_liked_price:.2f}\n"
                    message += f"   Avg. disliked price: ${avg_disliked_price:.2f}\n\n"

                # Room preferences
                avg_liked_beds = sum(f.bedrooms for f in liked_listings) / len(liked_listings)
                avg_liked_baths = sum(f.bathrooms for f in liked_listings) / len(liked_listings)
                message += "*Space Preferences:*\n"
                message += f"🛏 Preferred bedrooms: {avg_liked_beds:.1f}\n"
                message += f"🚿 Preferred bathrooms: {avg_liked_baths:.1f}\n\n"

                # Rating analysis
                avg_liked_rating = sum(f.rating for f in liked_listings) / len(liked_listings)
                message += "*Rating Preferences:*\n"
                message += f"⭐ You prefer highly-rated listings (avg. {avg_liked_rating:.1f} stars)\n\n"

            # Get current preferences
            preferences = user.get_preferences()
            if preferences:
                message += "*Current Search Settings:*\n"
                if 'location' in preferences:
                    message += f"📍 Location: {preferences['location']}\n"
                if 'guests' in preferences:
                    message += f"👥 Guests: {preferences['guests']}\n"
                if 'selected_amenities' in preferences:
                    amenities = [self.amenities_options[a] for a in preferences['selected_amenities']]
                    message += f"✨ Preferred amenities: {', '.join(amenities)}\n\n"

            # Learning status
            learning_score = min((len(feedback) / 10) * 100, 100)  # Cap at 100%
            message += "*Learning Progress:*\n"
            message += f"🎯 I'm currently at {learning_score:.0f}% of understanding your preferences\n"
            message += "(Based on the amount of feedback received)\n\n"

            message += "💡 *Tip:* The more feedback you provide on listings, the better I can tailor recommendations to your taste!"

            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in stats command: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, there was an error retrieving your statistics."
            )

    async def cancel(self, update: Update, context: CallbackContext):
        """Cancel the conversation"""
        logger.info(f"Search cancelled by user {update.effective_user.id}")
        await update.message.reply_text(
            "Search cancelled. Use /search to start a new search!"
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update:
            await update.message.reply_text(
                "Sorry, something went wrong. Please try again later!"
            )
    
    def run(self):
        """Start the bot"""
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is running!")

def setup_bot():
    """Setup and run the bot"""
    bot = AirbnbBot()
    return bot  # Return the bot instance instead of running it directly
