# Text To Video AI Generator 🎬

Convert text into engaging videos using AI. This tool automatically generates videos by creating audio narration, finding relevant background footage, and adding captions.

## 🌟 Features

- Text-to-Speech narration using OpenAI's API
- Automatic background video selection from Pexels
- Synchronized captions
- Smart video scene transitions
- Automated script generation (optional)

## 🚀 Prerequisites

- Python 3.x
- OpenAI API key
- Pexels API key

## ⚙️ Installation

1. Clone the repository:

```bash
git clone [your-repo-url]
cd text-to-video-ai
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   Create a `.env` file in the root directory and add:

```bash
OPENAI_API_KEY="your-openai-key"
PEXELS_API_KEY="your-pexels-key"
```

## 🎯 Usage

Run the script with your desired text:

```bash
python app.py "Your text content here"
```

The generated video will be saved as `rendered_video.mp4` in the project directory.

## 🛠️ Project Structure

- `app.py` - Main application file
- `utility/`
  - `audio/` - Audio generation utilities
  - `script/` - Script generation utilities
  - `video/` - Video processing utilities
  - `render/` - Video rendering engine
  - `captions/` - Caption generation utilities

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Show Your Support

If you find this project useful, please give it a star on GitHub!

## 💁 Contribution

As an open-source project we are extremely open to contributions. To get started raise an issue in Github or create a pull request
