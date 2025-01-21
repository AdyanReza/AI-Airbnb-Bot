import logging
from dotenv import load_dotenv
from app.bot.telegram_bot import AirbnbBot
from app.models.database import init_db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Load environment variables
        load_dotenv()
        logger.debug("Environment variables loaded")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.debug("Database initialized")
        
        # Start the bot
        logger.info("Starting Telegram bot...")
        bot = AirbnbBot()
        application = bot.application
        
        logger.info("Bot setup completed, starting polling...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
