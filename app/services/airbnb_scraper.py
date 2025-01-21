from typing import Dict, List, Optional
from datetime import datetime
import logging
import requests
from urllib.parse import quote, urlencode
import json

logger = logging.getLogger(__name__)

class AirbnbAPI:
    """
    Interacts with Airbnb's API through RapidAPI to search for listings.
    """
    
    def __init__(self, api_key: str = None):
        self.base_url = "https://airbnb13.p.rapidapi.com"
        self.api_key = api_key
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "airbnb13.p.rapidapi.com"
        }
        
        # Map amenity IDs to their names
        self.amenity_id_mapping = {
            1: "tv",
            4: "wifi",
            5: "air conditioning",
            8: "kitchen",
            9: "parking",
            33: "washer",
            34: "dryer",
            35: "heating",
            36: "dedicated workspace",
            40: "pool",
            44: "kitchen",
            45: "wifi",
            46: "parking",
            57: "heating",
            73: "kitchen",
            77: "wifi",
            79: "parking",
            89: "air conditioning",
            90: "heating",
            91: "wifi",
            92: "kitchen",
            93: "parking",
            94: "washer",
            96: "dryer",
            101: "tv",
            137: "kitchen",
            236: "wifi",
            251: "parking",
            308: "kitchen",
            415: "wifi",
            522: "parking",
            671: "kitchen"
        }
        
        # Map our amenity keys to possible variations
        self.amenity_variations = {
            "wifi": ["wifi", "wireless internet", "internet"],
            "kitchen": ["kitchen", "full kitchen", "private kitchen"],
            "parking": ["parking", "free parking", "private parking"],
            "washer": ["washer", "washing machine", "laundry"],
            "dryer": ["dryer", "clothes dryer"],
            "ac": ["air conditioning", "ac", "air-conditioning"],
            "heating": ["heating", "heat"],
            "tv": ["tv", "television", "cable tv"],
            "workspace": ["workspace", "dedicated workspace", "laptop friendly"]
        }
    
    def _get_amenities_from_ids(self, amenity_ids: List[int]) -> List[str]:
        """Convert amenity IDs to their corresponding names."""
        amenities = []
        for aid in amenity_ids:
            if aid in self.amenity_id_mapping:
                amenities.append(self.amenity_id_mapping[aid])
        return list(set(amenities))  # Remove duplicates
    
    def _check_amenities(self, listing_amenities: List[str], required_amenities: List[str]) -> bool:
        """Check if listing has all required amenities."""
        if not required_amenities:
            return True
            
        listing_amenities_lower = [a.lower() for a in listing_amenities]
        logger.debug(f"Checking amenities: {listing_amenities_lower} against required: {required_amenities}")
        
        for required in required_amenities:
            required_lower = required.lower()
            variations = self.amenity_variations.get(required_lower, [required_lower])
            
            found = False
            for variation in variations:
                if any(variation in amenity or amenity in variation for amenity in listing_amenities_lower):
                    found = True
                    break
            
            if not found:
                logger.debug(f"Missing required amenity: {required}")
                return False
        
        return True
    
    def _parse_price(self, price_data: Optional[Dict]) -> Optional[int]:
        """Parse price from the API response."""
        if not price_data:
            return None
            
        try:
            logger.info(f"Raw price data: {price_data}")
            
            if isinstance(price_data, dict) and price_data.get('priceItems'):
                # Extract the dollar amount from the title (e.g. "$171 x 3 nights")
                title = price_data['priceItems'][0].get('title', '')
                if '$' in title and 'x' in title:
                    try:
                        # Get the number after the $ and before the x
                        price_str = title.split('$')[1].split('x')[0].strip()
                        logger.info(f"Extracted price from title: {price_str}")
                        return int(float(price_str))
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse price from title {title}: {e}")
            
            logger.error(f"Could not parse price from data: {price_data}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing price: {e}", exc_info=True)
            return None

    def _get_listing_amenities(self, item: Dict) -> List[str]:
        """Extract all amenities from a listing item, handling various formats."""
        amenities = []
        
        # Check all possible amenity fields
        amenity_fields = [
            "previewAmenities",
            "amenities",
            "amenityIds",
            "amenitiesIds",  # Some listings use this format
            "listingAmenities",
            "facilities",
            "features"
        ]
        
        for field in amenity_fields:
            field_value = item.get(field)
            if not field_value:
                continue
                
            # Handle different data types
            if isinstance(field_value, str):
                amenities.append(field_value)
            elif isinstance(field_value, list):
                for amenity in field_value:
                    if isinstance(amenity, dict):
                        # Handle amenity objects with name/id fields
                        name = amenity.get('name') or amenity.get('title') or amenity.get('text')
                        if name:
                            amenities.append(str(name))
                    else:
                        amenities.append(str(amenity))
            elif isinstance(field_value, dict):
                # Some APIs return amenities as a dict with values
                for value in field_value.values():
                    if value:
                        amenities.append(str(value))
        
        # Also check for amenities in the listing description
        description = str(item.get('description', ''))
        if description:
            # Add common amenity indicators from description
            indicators = ['included:', 'amenities:', 'features:', 'facilities:']
            for indicator in indicators:
                if indicator in description.lower():
                    amenities.append(description)
                    break
        
        logger.debug(f"Extracted amenities: {amenities}")
        return amenities
        
    def search_listings(self,
                       location: str,
                       check_in: str,
                       check_out: str,
                       guests: int = 1,
                       min_price: Optional[int] = None,
                       max_price: Optional[int] = None,
                       amenities: Optional[List[str]] = None) -> List[Dict]:
        """
        Search for Airbnb listings using the RapidAPI endpoint.
        """
        try:
            # Format the search parameters
            params = {
                "location": location,
                "checkin": check_in,
                "checkout": check_out,
                "adults": str(guests),
                "children": "0",
                "infants": "0",
                "pets": "0",
                "page": "1",
                "currency": "USD",
                "priceMin": str(min_price) if min_price else None,
                "priceMax": str(max_price) if max_price else None
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            logger.info(f"Searching with params: {json.dumps(params, indent=2)}")
            
            # Make the API request
            response = requests.get(
                f"{self.base_url}/search-location",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
            
            # Parse the response
            try:
                data = response.json()
                # Log full response for debugging
                logger.info("Full API response:")
                logger.info(json.dumps(data, indent=2))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API response: {e}")
                return []
            
            results = data.get("results", [])
            if not results:
                logger.warning("No results found in API response")
                return []
                
            logger.info(f"Found {len(results)} listings in API response")
            
            listings = []
            for item in results:
                try:
                    # Log raw listing data
                    logger.info(f"Raw listing data for {item.get('id')}:")
                    logger.info(json.dumps(item, indent=2))
                    
                    # Parse price
                    price_amount = self._parse_price(item.get("price"))
                    if price_amount is None:
                        logger.warning(f"Skipping listing {item.get('id')}: Could not parse price from {item.get('price')}")
                        continue
                    
                    listing = {
                        "title": str(item.get("name", "")),
                        "price": int(price_amount),
                        "rating": float(item.get("rating", 0) or 0),
                        "reviews": int(item.get("reviewsCount", 0) or 0),
                        "location": f"{item.get('city', '')} {item.get('country', '')}".strip() or location,
                        "url": f"https://www.airbnb.com/rooms/{item.get('id')}",
                        "bedrooms": float(item.get("bedrooms", 0) or 0),
                        "bathrooms": float(item.get("bathrooms", 0) or 0),
                        "max_guests": int(item.get("maxGuests", 0) or item.get("persons", 0) or 0),
                        "amenities": item.get('previewAmenities', [])
                    }
                    listings.append(listing)
                    logger.info(f"Successfully added listing: {item.get('id')} with price {price_amount}")
                    
                except Exception as e:
                    logger.error(f"Error parsing listing: {e}", exc_info=True)
                    continue
            
            # Sort listings by price and take top 5
            listings.sort(key=lambda x: x["price"])
            listings = listings[:5]
            
            logger.info(f"Returning {len(listings)} listings")
            return listings
            
        except Exception as e:
            logger.error(f"Error searching listings: {e}", exc_info=True)
            return []

            listings.sort(key=lambda x: x["price"])
            listings = listings[:5]
            
            return listings
            
        except Exception as e:
            logger.error(f"Error searching listings: {e}", exc_info=True)
            return []
