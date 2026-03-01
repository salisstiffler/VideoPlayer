# VideoPlayer (PornGemini)

A multi-platform video player application with a specialized scraper backend. The project is divided into two main parts: a Flutter-based client and a FastAPI-based server.

## Project Structure

- `client/`: Flutter mobile application.
- `server/`: FastAPI server for video scraping and metadata extraction.

## Features

- **Multi-site Scraping:** Supports content extraction from Pornhub, XVideos, XNXX, and 51cg1.
- **Base64 Thumbnails:** All thumbnails are converted to base64 for reliable loading.
- **Streaming Proxy:** Includes a proxy service to bypass some regional or header-based restrictions during streaming.
- **Cross-Platform:** The client is built with Flutter, targeting Android, Windows, and Web.

## Server Setup (Python)

The server acts as the backend API for the application.

### Prerequisites

- Python 3.9+
- Pip

### Local Development

1. Navigate to the `server/` directory:
   ```bash
   cd server
   ```
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`.

### Docker Deployment

1. Navigate to the `server/` directory:
   ```bash
   cd server
   ```
2. Build and run with Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

## Client Setup (Flutter)

The client application connects to the backend API.

### Prerequisites

- Flutter SDK (stable channel)
- Android Studio / VS Code with Flutter extension

### Running the Client

1. Navigate to the `client/` directory:
   ```bash
   cd client
   ```
2. Fetch dependencies:
   ```bash
   flutter pub get
   ```
3. Run the application:
   ```bash
   flutter run
   ```

## API Endpoints

- `GET /sites`: List available sites.
- `GET /videos?site={site}&page={page}`: Get a list of videos from a specific site.
- `GET /video_info?url={url}`: Extract detailed video information and playable formats.
- `GET /stream?url={url}&headers={headers}`: Proxy stream for media content.
- `GET /health`: Health check endpoint.

## License

Private Project - All rights reserved.
