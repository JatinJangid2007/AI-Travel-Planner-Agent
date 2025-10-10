import requests
from typing import Dict, Any, List
import os
import json
import requests
from datetime import datetime, date, timedelta

class FlightSearchTool:
    def __init__(self):
        self.api_key = os.getenv("AMADEUS_API_KEY")
        self.api_secret = os.getenv("AMADEUS_API_SECRET")
        self.access_token = None
        self.token_expiry = None
        
        #city to airport code mapping
        self.city_to_iata = {
            # India
            "delhi": "DEL", "new delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR",
            "bengaluru": "BLR", "chennai": "MAA", "kolkata": "CCU", "hyderabad": "HYD",
            "pune": "PNQ", "ahmedabad": "AMD", "jaipur": "JAI", "goa": "GOI",
            "kochi": "COK", "cochin": "COK", "trivandrum": "TRV", "mangalore": "IXE",
            "mangaluru": "IXE", "lucknow": "LKO", "chandigarh": "IXC", "guwahati": "GAU",
            
            # Middle East
            "dubai": "DXB", "abu dhabi": "AUH", "doha": "DOH", "riyadh": "RUH",
            "jeddah": "JED", "muscat": "MCT", "kuwait": "KWI", "bahrain": "BAH",
            
            # Europe
            "london": "LHR", "paris": "CDG", "amsterdam": "AMS", "frankfurt": "FRA",
            "madrid": "MAD", "barcelona": "BCN", "rome": "FCO", "milan": "MXP",
            "zurich": "ZRH", "vienna": "VIE", "brussels": "BRU", "munich": "MUC",
            "istanbul": "IST", "athens": "ATH", "lisbon": "LIS", "copenhagen": "CPH",
            
            # Americas
            "new york": "JFK", "los angeles": "LAX", "chicago": "ORD", "miami": "MIA",
            "san francisco": "SFO", "boston": "BOS", "washington": "IAD", "seattle": "SEA",
            "toronto": "YYZ", "vancouver": "YVR", "mexico city": "MEX",
            
            # Asia Pacific
            "tokyo": "NRT", "singapore": "SIN", "hong kong": "HKG", "bangkok": "BKK",
            "kuala lumpur": "KUL", "manila": "MNL", "seoul": "ICN", "beijing": "PEK",
            "shanghai": "PVG", "sydney": "SYD", "melbourne": "MEL", "auckland": "AKL",
            
            # Africa
            "cairo": "CAI", "johannesburg": "JNB", "cape town": "CPT", "nairobi": "NBO",
            "lagos": "LOS", "casablanca": "CMN"
        }
        
        # Country to currency mapping for better pricing
        self.country_currency = {
            "DEL": "INR", "BOM": "INR", "BLR": "INR", "MAA": "INR", "CCU": "INR",
            "HYD": "INR", "IXE": "INR", "GOI": "INR", "COK": "INR", "PNQ": "INR",
            "DXB": "AED", "AUH": "AED", "DOH": "QAR", "RUH": "SAR",
            "LHR": "GBP", "CDG": "EUR", "FRA": "EUR", "AMS": "EUR",
            "JFK": "USD", "LAX": "USD", "ORD": "USD", "SFO": "USD",
            "NRT": "JPY", "SIN": "SGD", "HKG": "HKD", "BKK": "THB"
        }
    
    def _get_iata_code(self, city: str) -> str:
        """Convert city name to IATA airport code"""
        city_lower = city.lower().strip()
        
        # If already a 3-letter code, return uppercase
        if len(city_lower) == 3 and city_lower.isalpha():
            return city_lower.upper()
        
        # Look up in mapping
        iata = self.city_to_iata.get(city_lower)
        if iata:
            return iata
        
        # If not found, try to extract first 3 letters (last resort)
        # This is risky but better than failing completely
        return city[:3].upper()
    
    def _get_currency(self, origin_code: str, dest_code: str) -> str:
        """Determine appropriate currency based on route"""
        # Prefer origin country currency
        currency = self.country_currency.get(origin_code)
        if currency:
            return currency
        
        # Fallback to destination currency
        currency = self.country_currency.get(dest_code)
        if currency:
            return currency
        
        # Default to USD
        return "USD"
    
    def get_access_token(self):
        """Get Amadeus access token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"] - 60)
            return self.access_token
        except Exception as e:
            print(f"Error getting Amadeus token: {e}")
            return None
    
    def search(self, origin: str, destination: str, departure_date: str, return_date: str = None) -> List[Dict]:
        """Search for flights"""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get Amadeus access token. Please check your API credentials.")
        
        # Convert city names to IATA codes
        origin_code = self._get_iata_code(origin)
        dest_code = self._get_iata_code(destination)
        
        # Determine appropriate currency
        currency = self._get_currency(origin_code, dest_code)
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest_code,
            "departureDate": departure_date,
            "adults": 1,
            "currencyCode": currency,  # Request prices in appropriate currency
            "max": 3
        }
        
        if return_date:
            params["returnDate"] = return_date
        
        print(f"Searching flights: {origin} ({origin_code}) → {destination} ({dest_code}) on {departure_date}, currency: {currency}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        flights = []
        seen_flights = set()  # To avoid duplicates
        
        for offer in data.get("data", []):
            # Create unique identifier for flight
            first_segment = offer["itineraries"][0]["segments"][0]
            last_segment = offer["itineraries"][0]["segments"][-1]
            
            flight_key = (
                first_segment["departure"]["at"],
                last_segment["arrival"]["at"],
                offer["validatingAirlineCodes"][0] if offer.get("validatingAirlineCodes") else ""
            )
            
            # Skip if we've seen this exact flight
            if flight_key in seen_flights:
                continue
            
            seen_flights.add(flight_key)
            
            # Extract airline code and name
            airline_code = offer["validatingAirlineCodes"][0] if offer.get("validatingAirlineCodes") else "N/A"
            
            # Common airline code to name mapping
            airline_names = {
                "6E": "IndiGo", "AI": "Air India", "SG": "SpiceJet", "UK": "Vistara",
                "9W": "Jet Airways", "G8": "Go Air", "I5": "AirAsia India",
                "EK": "Emirates", "EY": "Etihad", "QR": "Qatar Airways", "SV": "Saudia",
                "BA": "British Airways", "LH": "Lufthansa", "AF": "Air France", "KL": "KLM",
                "TK": "Turkish Airlines", "SQ": "Singapore Airlines", "CX": "Cathay Pacific"
            }
            
            airline_display = airline_names.get(airline_code, airline_code)
            
            flight_info = {
                "price": f"{offer['price']['total']} {offer['price']['currency']}",
                "airline": f"{airline_display} ({airline_code})",
                "departure": first_segment["departure"]["at"],
                "arrival": last_segment["arrival"]["at"],
                "duration": offer["itineraries"][0]["duration"],
                "stops": len(offer["itineraries"][0]["segments"]) - 1
            }
            flights.append(flight_info)
            
            if len(flights) >= 3:
                break
        
        if not flights:
            raise Exception(f"No flights found for {origin} ({origin_code}) to {destination} ({dest_code}) on {departure_date}")
        
        return flights

import requests
from datetime import datetime, timedelta, date
from typing import List, Dict

class WeatherTool:
    """Get weather forecast using Open-Meteo API (free, no key required)"""

    def __init__(self):
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.climate_url = "https://climate-api.open-meteo.com/v1/climate"
        self.forecast_days_limit = 16  # Open-Meteo supports ~16-day forecast

    def get_coordinates(self, city: str) -> tuple:
        """Get latitude and longitude for a city"""
        response = requests.get(self.geocoding_url, params={"name": city, "count": 1}, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            result = data["results"][0]
            return result["latitude"], result["longitude"]

        raise Exception(f"Could not find coordinates for city: {city}")

    def get_forecast(self, city: str, start_date: str, end_date: str) -> List[Dict]:
        """Get weather forecast for date range or use historical averages beyond 16 days"""
        lat, lon = self.get_coordinates(city)

        today = date.today()
        allowed_max = today + timedelta(days=self.forecast_days_limit)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        days_range = (end_dt - start_dt).days + 1

        # --- Case 1: Forecast available ---
        if start_dt <= allowed_max:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "auto"
            }

            response = requests.get(self.forecast_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})

            forecast = []
            for i in range(len(daily.get("time", []))):
                condition = self._weather_code_to_condition(daily["weathercode"][i])
                forecast.append({
                    "date": daily["time"][i],
                    "temp_max": f"{daily['temperature_2m_max'][i]}°C",
                    "temp_min": f"{daily['temperature_2m_min'][i]}°C",
                    "condition": condition
                })
            return forecast

        # --- Case 2: Beyond forecast range (use historical climate averages) ---
        climate_params = {
            "latitude": lat,
            "longitude": lon,
            "month": start_dt.month,
            "daily": "temperature_2m_max_mean,temperature_2m_min_mean",
        }

        try:
            response = requests.get(self.climate_url, params=climate_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            temp_max = data["daily"]["temperature_2m_max_mean"][0]
            temp_min = data["daily"]["temperature_2m_min_mean"][0]
        except Exception:
            temp_max, temp_min = 25, 18  # fallback defaults

        # 🔁 Create pseudo-daily entries so planner doesn’t break
        forecast = []
        for i in range(days_range):
            current_day = start_dt + timedelta(days=i)
            forecast.append({
                "date": str(current_day),
                "temp_max": f"{temp_max:.1f}°C",
                "temp_min": f"{temp_min:.1f}°C",
                "condition": "🌡️ Estimated from historical climate averages"
            })

        return forecast

    def _weather_code_to_condition(self, code: int) -> str:
        conditions = {
            0: "☀️ Clear sky", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
            45: "🌫️ Foggy", 48: "🌫️ Fog", 51: "🌦️ Light drizzle", 53: "🌦️ Drizzle", 55: "🌧️ Heavy drizzle",
            61: "🌧️ Light rain", 63: "🌧️ Rain", 65: "🌧️ Heavy rain", 71: "🌨️ Light snow",
            73: "❄️ Snow", 75: "❄️ Heavy snow", 80: "🌦️ Light showers", 81: "🌧️ Showers",
            82: "⛈️ Heavy showers", 95: "⛈️ Thunderstorm", 96: "⛈️ Thunderstorm with hail",
            99: "⛈️ Severe thunderstorm"
        }
        return conditions.get(code, "🌡️ Unknown condition")

        
        

    # -------------------------------------------------------------------
    def _weather_code_to_condition(self, code: int) -> str:
        """Translate Open-Meteo weather codes to human-readable text"""
        conditions = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy",
            51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
            61: "Light rain", 63: "Rain", 65: "Heavy rain",
            71: "Light snow", 73: "Snow", 75: "Heavy snow",
            80: "Light showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm"
        }
        return conditions.get(code, "Unknown")

    # -------------------------------------------------------------------
    def _condition_to_emoji(self, condition: str) -> str:
        """Add weather emoji for better visualization"""
        mapping = {
            "Clear": "☀️",
            "Mainly clear": "🌤️",
            "Partly cloudy": "⛅",
            "Overcast": "☁️",
            "Fog": "🌫️",
            "Drizzle": "🌦️",
            "Rain": "🌧️",
            "Showers": "🌦️",
            "Snow": "❄️",
            "Thunderstorm": "⛈️",
            "Unknown": "❔"
        }

        for key, emoji in mapping.items():
            if key.lower() in condition.lower():
                return emoji
        return "🌡️"




class POITool:
    """Get Points of Interest using Wikipedia API"""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.headers = {
            'User-Agent': 'TravelPlannerBot/1.0 (Educational Project)'
        }
    
    def get_attractions(self, city: str) -> List[Dict]:
        """Fetch real tourist attractions for a city using Wikipedia API"""
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"top tourist attractions in {city}",
            "srlimit": 10
        }

        response = requests.get(self.base_url, params=search_params, headers=self.headers, timeout=30)
        response.raise_for_status()
        search_data = response.json()

        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            raise Exception(f"No attractions found for {city}")

        attractions = []

        for result in search_results:
            page_title = result["title"]

            # 🧠 Skip generic or irrelevant pages
            if any(skip in page_title.lower() for skip in [
                "list of", "tourist attractions", "lists of", "history of", "culture of"
            ]):
                continue

            content_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "titles": page_title
            }

            try:
                content_response = requests.get(self.base_url, params=content_params, headers=self.headers, timeout=10)
                content_response.raise_for_status()
                content_data = content_response.json()

                pages = content_data.get("query", {}).get("pages", {})
                page = list(pages.values())[0]

                extract = page.get("extract", "")
                description = extract.strip()
                if not description:
                    description = "A popular landmark and tourist spot in the city."

                attractions.append({
                    "name": page_title,
                    "description": description[:500]
                })
            except Exception:
                continue

        # 🧩 If Wikipedia only returned generic pages, fall back to at least something
        if not attractions:
            raise Exception(f"Could not retrieve detailed attractions for {city}")

        return attractions[:8]
