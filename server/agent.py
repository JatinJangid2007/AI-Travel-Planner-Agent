from typing import TypedDict, Annotated, Sequence
from langgraph.graph import Graph, StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
import operator
import re
from datetime import datetime, timedelta
import os
from toolss import FlightSearchTool, WeatherTool, POITool

# Define the state of our agent
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    origin: str
    destination: str
    start_date: str
    end_date: str
    flights: list
    weather: list
    attractions: list
    plan: dict
    steps: list

class TravelPlannerAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",   # you can also try "llama-3.1-8b-instant"
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Initialize tools
        self.flight_tool = FlightSearchTool()
        self.weather_tool = WeatherTool()
        self.poi_tool = POITool()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("parse_query", self.parse_query)
        workflow.add_node("search_flights", self.search_flights)
        workflow.add_node("get_weather", self.get_weather)
        workflow.add_node("get_attractions", self.get_attractions)
        workflow.add_node("create_plan", self.create_plan)
        
        # Define edges
        workflow.set_entry_point("parse_query")
        workflow.add_edge("parse_query", "search_flights")
        workflow.add_edge("search_flights", "get_weather")
        workflow.add_edge("get_weather", "get_attractions")
        workflow.add_edge("get_attractions", "create_plan")
        workflow.add_edge("create_plan", END)
        
        return workflow.compile()
    
    def parse_query(self, state: AgentState) -> AgentState:
        query = state["query"]
        steps = state.get("steps", [])
        
        # Use LLM to extract entities
        prompt = f"""Extract travel information from this query: "{query}"

Return a JSON with these fields:
- origin: departure CITY NAME (not airport code)
- destination: arrival CITY NAME (not airport code)
- start_date: departure date (YYYY-MM-DD format)
- end_date: return date (YYYY-MM-DD format)

IMPORTANT: Extract full city names like "Dubai", "Istanbul", "Paris", NOT airport codes like "DXB", "IST", "CDG".

If dates are relative (like "next month"), calculate based on today's date: {datetime.now().strftime('%Y-%m-%d')}

Example output:
{{"origin": "Dubai", "destination": "Istanbul", "start_date": "2024-11-10", "end_date": "2024-11-15"}}

Only respond with valid JSON, no other text."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # Extract JSON from response
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
            else:
                extracted = json.loads(content)
            
            state["origin"] = extracted.get("origin", "")
            state["destination"] = extracted.get("destination", "")
            state["start_date"] = extracted.get("start_date", "")
            state["end_date"] = extracted.get("end_date", "")
            
            steps.append({
                "tool": "parse_query",
                "input": {"query": query},
                "output": extracted,
                "status": "success"
            })
            state["steps"] = steps
            
        except Exception as e:
            print(f"Parse error: {e}")
            # Fallback to basic regex parsing
            state["origin"] = self._extract_city(query, first=True)
            state["destination"] = self._extract_city(query, first=False)
            state["start_date"] = self._extract_date(query)
            state["end_date"] = self._extract_date(query, return_date=True)
            
            steps.append({
                "tool": "parse_query",
                "input": {"query": query},
                "output": {
                    "origin": state["origin"],
                    "destination": state["destination"],
                    "start_date": state["start_date"],
                    "end_date": state["end_date"]
                },
                "status": "failed",
                "error": str(e)
            })
            state["steps"] = steps
        
        return state
    
    def search_flights(self, state: AgentState) -> AgentState:
        steps = state.get("steps", [])
        
        try:
            flights = self.flight_tool.search(
                origin=state["origin"],
                destination=state["destination"],
                departure_date=state["start_date"],
                return_date=state.get("end_date")
            )
            
            state["flights"] = flights
            steps.append({
                "tool": "flight_search",
                "input": {
                    "origin": state["origin"],
                    "destination": state["destination"],
                    "departure_date": state["start_date"]
                },
                "output": flights,
                "status": "success"
            })
            state["steps"] = steps
            
        except Exception as e:
            print(f"Flight search error: {e}")
            state["flights"] = []
            steps.append({
                "tool": "flight_search",
                "input": {
                    "origin": state["origin"],
                    "destination": state["destination"],
                    "departure_date": state["start_date"]
                },
                "output": [],
                "status": "failed",
                "error": str(e)
            })
            state["steps"] = steps
        
        return state
    
    def get_weather(self, state: AgentState) -> AgentState:
        steps = state.get("steps", [])
        
        try:
            destination = state["destination"]
            if len(destination) == 3:
                # Common airport code to city mappings
                airport_to_city = {
                    "IST": "Istanbul", "DXB": "Dubai", "CDG": "Paris", "LHR": "London",
                    "JFK": "New York", "LAX": "Los Angeles", "NRT": "Tokyo", "SIN": "Singapore",
                    "HKG": "Hong Kong", "BKK": "Bangkok", "DEL": "Delhi", "BOM": "Mumbai",
                    "SYD": "Sydney", "MEL": "Melbourne", "BCN": "Barcelona", "MAD": "Madrid",
                    "FCO": "Rome", "AMS": "Amsterdam", "FRA": "Frankfurt", "MUC": "Munich"
                }
                destination = airport_to_city.get(destination.upper(), destination)
            
            weather = self.weather_tool.get_forecast(
                city=destination,
                start_date=state["start_date"],
                end_date=state["end_date"]
            )
            
            state["weather"] = weather
            steps.append({
                "tool": "weather_forecast",
                "input": {
                    "city": destination,
                    "start_date": state["start_date"],
                    "end_date": state["end_date"]
                },
                "output": weather,
                "status": "success"
            })
            state["steps"] = steps
            
        except Exception as e:
            print(f"Weather error: {e}")
            state["weather"] = []
            steps.append({
                "tool": "weather_forecast",
                "input": {
                    "city": state.get("destination", ""),
                    "start_date": state.get("start_date", ""),
                    "end_date": state.get("end_date", "")
                },
                "output": [],
                "status": "failed",
                "error": str(e)
            })
            state["steps"] = steps
        
        return state
    
    def get_attractions(self, state: AgentState) -> AgentState:
        steps = state.get("steps", [])
        
        try:
            destination = state["destination"]
            if len(destination) == 3:
                # Common airport code to city mappings
                airport_to_city = {
                    "IST": "Istanbul", "DXB": "Dubai", "CDG": "Paris", "LHR": "London",
                    "JFK": "New York", "LAX": "Los Angeles", "NRT": "Tokyo", "SIN": "Singapore",
                    "HKG": "Hong Kong", "BKK": "Bangkok", "DEL": "Delhi", "BOM": "Mumbai",
                    "SYD": "Sydney", "MEL": "Melbourne", "BCN": "Barcelona", "MAD": "Madrid",
                    "FCO": "Rome", "AMS": "Amsterdam", "FRA": "Frankfurt", "MUC": "Munich"
                }
                destination = airport_to_city.get(destination.upper(), destination)
            
            attractions = self.poi_tool.get_attractions(city=destination)
            
            state["attractions"] = attractions
            steps.append({
                "tool": "attractions",
                "input": {"city": destination},
                "output": attractions,
                "status": "success"
            })
            state["steps"] = steps
            
        except Exception as e:
            print(f"Attractions error: {e}")
            state["attractions"] = []
            steps.append({
                "tool": "attractions",
                "input": {"city": state.get("destination", "")},
                "output": [],
                "status": "failed",
                "error": str(e)
            })
            state["steps"] = steps
        
        return state
    
    def create_plan(self, state: AgentState) -> AgentState:
        # Calculate number of days
        start = datetime.strptime(state["start_date"], "%Y-%m-%d")
        end = datetime.strptime(state["end_date"], "%Y-%m-%d")
        num_days = (end - start).days + 1
        
        # Create day-by-day plan
        daily_plan = []
        attractions = state.get("attractions", [])
        weather = state.get("weather", [])
        
        for i in range(num_days):
            day_date = start + timedelta(days=i)
            day_weather = weather[i] if i < len(weather) else {}
            
            # Distribute attractions across days
            day_attractions = attractions[i*2:(i+1)*2] if attractions else []
            
            day_plan = {
                "day": i + 1,
                "date": day_date.strftime("%Y-%m-%d"),
                "weather": day_weather,
                "activities": []
            }
            
            if i == 0:
                day_plan["activities"].append({
                    "time": "Morning",
                    "activity": f"Arrival in {state['destination']}",
                    "description": "Check into hotel and rest"
                })
            
            for j, attraction in enumerate(day_attractions):
                time_slot = "Afternoon" if j == 0 else "Evening"
                day_plan["activities"].append({
                    "time": time_slot,
                    "activity": f"Visit {attraction['name']}",
                    "description": attraction.get('description', '')
                })
            
            if i == num_days - 1:
                day_plan["activities"].append({
                    "time": "Evening",
                    "activity": "Departure",
                    "description": f"Return flight to {state['origin']}"
                })
            
            daily_plan.append(day_plan)
        
        # Create summary
        summary = self._generate_summary(state, daily_plan)
        
        plan = {
            "origin": state["origin"],
            "destination": state["destination"],
            "start_date": state["start_date"],
            "end_date": state["end_date"],
            "duration_days": num_days,
            "flights": state.get("flights", []),
            "daily_plan": daily_plan,
            "summary": summary
        }
        
        state["plan"] = plan
        return state
    
    def _generate_summary(self, state, daily_plan):
        """Generate natural language summary"""
        summary = f"Travel Plan: {state['origin']} to {state['destination']}\n\n"
        summary += f"Duration: {state['start_date']} to {state['end_date']}\n\n"
        
        if state.get("flights"):
            summary += "Flight Options:\n"
            for i, flight in enumerate(state["flights"][:3], 1):
                summary += f"  {i}. {flight['airline']} - {flight['price']}\n"
        
        summary += "\nDaily Itinerary:\n"
        for day in daily_plan:
            summary += f"\nDay {day['day']} ({day['date']}):\n"
            if day.get('weather'):
                summary += f"  Weather: {day['weather'].get('condition', 'N/A')}, {day['weather'].get('temp_max', 'N/A')}\n"
            for activity in day['activities']:
                summary += f"  • {activity['time']}: {activity['activity']}\n"
        
        return summary
    
    def _extract_city(self, text, first=True):
        """Basic city extraction (fallback)"""
        # This is a simplified approach
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ['from', 'to']:
                if i + 1 < len(words):
                    if first and word.lower() == 'from':
                        return words[i + 1].strip(',.')
                    elif not first and word.lower() == 'to':
                        return words[i + 1].strip(',.')
        return ""
    
    def _extract_date(self, text, return_date=False):
        """Basic date extraction (fallback)"""
        today = datetime.now()
        if return_date:
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")
        return today.strftime("%Y-%m-%d")
    
    def run(self, query: str):
        """Run the agent"""
        initial_state = {
            "messages": [],
            "query": query,
            "origin": "",
            "destination": "",
            "start_date": "",
            "end_date": "",
            "flights": [],
            "weather": [],
            "attractions": [],
            "plan": {},
            "steps": []
        }
        
        result = self.graph.invoke(initial_state)
        return result