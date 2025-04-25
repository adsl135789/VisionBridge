# VisionBridge 藝術體驗系統

[English](#visionbridge---art-experience-system) | [中文](#visionbridge-藝術體驗系統-1)

---

## VisionBridge - Art Experience System

### Introduction

VisionBridge is an AI-powered art experience system designed to make visual art accessible to everyone, including those with visual impairments. By combining advanced image recognition technology with cultural and personal context processing, VisionBridge provides detailed descriptions of artworks that go beyond mere object identification.

### Features

- **Artwork Analysis**: Uploads and analyzes images of artworks, generating comprehensive descriptions.
- **Cultural Context**: Personalizes descriptions based on cultural backgrounds, making art more relatable.
- **Personal Color Impressions**: Allows users to input their personal impressions of colors, which are integrated into the artwork descriptions.
- **Interactive Conversations**: Enables users to ask questions about the artwork and receive detailed responses.
- **Dual Interpretation Modes**: Offers both basic and personalized interpretation options.

### Technical Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **AI Model**: Google Gemini AI
- **Database**: MongoDB
- **Image Processing**: PIL (Python Imaging Library)

### Installation

1. Clone the repository:
   ```
   git clone [repository URL]
   cd VisionBridge
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file based on the `.env.example` template
   - Add your Gemini API key and MongoDB connection details

4. Run the application:
   ```
   python app.py
   ```

### Usage

1. Open your browser and navigate to `http://localhost:11316`
2. Upload an artwork image
3. Choose between basic and personalized interpretation
4. For personalized interpretation, select your cultural background and input color impressions
5. Start a conversation by asking questions about the artwork


