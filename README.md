# AI Travel Planner Agent

An intelligent travel planning system powered by LangGraph that orchestrates multiple APIs to create comprehensive day-by-day travel itineraries from natural language queries.

## Features

- **Natural Language Processing** - Understands flexible travel queries using grok ai LLM
- **Multi-Tool Orchestration** - Seamlessly integrates flights, weather, and attractions data
- **Google Authentication** - Secure sign-in with Firebase Auth
- **Persistent Storage** - User plans (history) saved to Firestore
- **Responsive UI** - Works on desktop, tablet, and mobile devices
- **Production Ready** - Containerized and deployable to Google Cloud Run

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **AI Framework**: LangGraph + LangChain
- **LLM**: Grok AI (llama 3.1) 
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **APIs**: Amadeus (Flights), Open-Meteo (Weather), Wikipedia (Attractions)
- **Deployment**: Docker + Google Cloud Run

## Project Structure

```
AI-Travel-Planner-Agent/
├── server/
│   ├── app.py                 # Flask REST API
│   ├── agent.py               # LangGraph agent
│   ├── tools.py               # API integrations
│   ├── firebase.py            # Firestore & Auth
│   ├── requirements.txt       # Dependencies
│   ├── Dockerfile            # Container config
│   └── static/
│       └── index.html        # Frontend UI
├── .env.example              # Environment template
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.11+
- Docker (optional)
- Google Cloud account (for deployment) (free trial)
- Firebase project (free)
- API Keys:
  - grok API key (free)
  - Amadeus API credentials (free)
  - Firebase service account (free)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Melaonn/AI-Travel-Planner-Agent
cd travel-planner-agent/server
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file:

```bash
# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-email@project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id

# API Keys
GROK_API_KEY=your-grok-key
AMADEUS_API_KEY=your-amadeus-key
AMADEUS_API_SECRET=your-amadeus-secret

# App Config
PORT=8080
ENVIRONMENT=development
```

enable web app in firebase and paste your web config in demo.html 

### 4. Run Locally

```bash
python app.py
```

Access at: `http://localhost:8080`

## API Endpoints

### POST /plan

Create a travel plan from natural language query.

**Request:**
```json
{
  "query": "I want to go from Dubai to Istanbul from Nov 10 to Nov 15"
}
```

**Response:**
```json
{
  "success": true,
  "plan_id": "abc123",
  "plan": {
    "origin": "Dubai",
    "destination": "Istanbul",
    "flights": [...],
    "daily_plan": [...],
    "summary": "..."
  },
  "steps": [...]
}
```

### GET /history?uid=

Get user's travel plan history.

**Parameters:**
- `uid` (authenticated with firebase user token)
- `limit` (default: 10)

### GET /health

Health check endpoint.


### Docker

```bash
# Build
docker build -t travel-planner-agent ./server

# Run
docker run -p 8080:8080 --env-file .env travel-planner-agent
```

## Configuration

### Firebase Setup

1. Create Firebase project
2. Enable Authentication (Google Sign-In)
3. Enable Firestore Database
4. Generate service account key
5. Add credentials to `.env`

### API Keys

- **Amadeus**: Register at [developers.amadeus.com](https://developers.amadeus.com)
- **Firebase**: Download from Firebase Console


## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request


## Support

For issues or questions, please open an issue on GitHub.

## Acknowledgments

- LangGraph by LangChain
- grok for LLM capabilities
- Amadeus for flight data
- Open-Meteo for weather data
- Firebase for backend infrastructure

---

**Built with ❤️ for the AI Developer **