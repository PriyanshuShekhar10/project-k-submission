import { useState, useEffect, useRef } from "react";
import axios from "axios";
import JSZip from "jszip";
import "./App.css";
import logo from "./assets/logo.png";

const API_BASE_URL = "http://localhost:5000/api/v1";
const OPENAI_API_KEY =
  "sk-proj----";

function App() {
  const [text, setText] = useState("");
  const [jobId, setJobId] = useState(null);
  const jobIdRef = useRef(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [mode, setMode] = useState("video"); // "video", "audio", or "book"
  const [theme, setTheme] = useState("light");
  const [bookFile, setBookFile] = useState(null);
  const [bookMetadata, setBookMetadata] = useState(null);
  const [selectedChapters, setSelectedChapters] = useState([]);
  const [voiceSettings, setVoiceSettings] = useState({
    type: "neutral",
    speed: 1.0,
    format: "mp3",
  });
  const [chapters, setChapters] = useState([]);
  const [bookName, setBookName] = useState("");
  const [parts, setParts] = useState([]);
  const [currentPart, setCurrentPart] = useState(0);
  const CHAR_LIMIT = 5000; // Maximum characters per part
  const [chapterParts, setChapterParts] = useState({});
  const [chapterPartsCount, setChapterPartsCount] = useState({});
  const [storyLength, setStoryLength] = useState("medium"); // short, medium, long
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);

  // Theme toggle effect
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const getDefaultMessage = (status, progress) => {
    switch (status) {
      case "queued":
        return "Job is queued for processing...";
      case "processing":
        return `Processing... ${progress}% complete`;
      case "completed":
        return "Generation completed successfully!";
      case "failed":
        return "Generation failed. Please try again.";
      default:
        return `Status: ${status}`;
    }
  };

  const checkStatus = async () => {
    // Use jobIdRef to get the persisted job id.
    const currentJobId = jobIdRef.current;
    if (!currentJobId) {
      console.log("No valid jobId provided for status check");
      setIsGenerating(false);
      setError("Invalid job ID. Please try generating again.");
      return;
    }

    try {
      console.log("Checking status for job:", currentJobId, "Mode:", mode);
      const endpoint = mode === "video" ? "/status" : "/audio-status";
      const response = await axios.get(
        `${API_BASE_URL}${endpoint}/${currentJobId}`
      );
      console.log("Status check response:", response.data);
      const { status, progress = 0, message = "" } = response.data;
      setStatus(status);
      setProgress(progress);
      setMessage(message || getDefaultMessage(status, progress));

      if (status === "completed" && progress === 100) {
        setIsGenerating(false);
        // Keep the jobId in state for download/playback.
      } else if (status === "failed") {
        setIsGenerating(false);
        // For definitive failure clear the job id.
        setJobId(null);
        jobIdRef.current = null;
        setError("Generation failed. Please try again.");
      } else {
        setTimeout(checkStatus, 2000);
      }
    } catch (error) {
      console.error("Status check error details:", {
        message: error.message,
        response: error.response,
        status: error.response?.status,
        endpoint: `${API_BASE_URL}${
          mode === "video" ? "/status" : "/audio-status"
        }/${currentJobId}`,
        mode,
      });

      // If we get a 404, it might mean the job is still processing.
      if (error.response?.status === 404) {
        setTimeout(checkStatus, 2000);
      } else {
        setIsGenerating(false);
        // Only clear the job id if necessary.
        setError("Failed to check generation status. Please try again.");
      }
    }
  };

  useEffect(() => {
    console.log("useEffect triggered with:", { jobId, isGenerating });
    let intervalId;

    // Only start checking if we have a valid jobId and isGenerating is true
    if (jobId && isGenerating) {
      console.log("Starting status check interval");
      // Check immediately
      checkStatus();

      // Then set up interval (optional since checkStatus uses setTimeout)
      intervalId = setInterval(() => {
        console.log("Interval triggered, checking status...");
        if (jobIdRef.current) {
          checkStatus();
        }
      }, 2000);
    }

    return () => {
      if (intervalId) {
        console.log("Clearing interval");
        clearInterval(intervalId);
      }
    };
  }, [jobId, isGenerating, mode]);

  const splitTextIntoParts = (text) => {
    const words = text.split(" ");
    const parts = [];
    let currentPart = "";

    for (const word of words) {
      if ((currentPart + " " + word).length <= CHAR_LIMIT) {
        currentPart = currentPart ? currentPart + " " + word : word;
      } else {
        parts.push(currentPart);
        currentPart = word;
      }
    }
    if (currentPart) {
      parts.push(currentPart);
    }
    return parts;
  };

  const handleTextChange = (e) => {
    const newText = e.target.value;
    setText(newText);
    if (newText.length > CHAR_LIMIT) {
      setParts(splitTextIntoParts(newText));
    } else {
      setParts([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsGenerating(true);
    console.log("Submitting text for generation");

    try {
      let endpoint;
      let payload = { text };

      if (mode === "book") {
        endpoint = `${API_BASE_URL}/generate-book`;
        // Create a FormData object for the book file
        const formData = new FormData();
        formData.append("file", bookFile);
        formData.append("chapters", JSON.stringify(selectedChapters));
        formData.append("voiceSettings", JSON.stringify(voiceSettings));

        const response = await axios.post(endpoint, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });

        console.log("Generate response:", response.data);
        setJobId(response.data.job_id);
        jobIdRef.current = response.data.job_id;
        setStatus("queued");
        setProgress(0);
        setMessage("Book generation started");
        console.log("Job started with ID:", response.data.job_id);
        return;
      } else {
        endpoint =
          mode === "video"
            ? `${API_BASE_URL}/generate`
            : `${API_BASE_URL}/generate-audio`;
      }

      const response = await axios.post(endpoint, payload);
      console.log("Generate response:", response.data);
      setJobId(response.data.job_id);
      jobIdRef.current = response.data.job_id;
      setStatus("queued");
      setProgress(0);
      setMessage(
        `${
          mode === "video" ? "Video" : mode === "audio" ? "Audio" : "Book"
        } generation started`
      );
      console.log("Job started with ID:", response.data.job_id);
    } catch (err) {
      console.error("Generate error details:", {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      setError("Error starting generation: " + err.message);
      setIsGenerating(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !file.name.toLowerCase().endsWith(".epub")) {
      setError("Please upload a valid EPUB file");
      return;
    }

    try {
      setBookName(file.name.replace(".epub", ""));
      const zip = new JSZip();
      const contents = await zip.loadAsync(file);
      setBookFile(file); // Store the file for later use

      // Find the OPF file
      let opfFile;
      let opfContent;
      for (const filename of Object.keys(contents.files)) {
        if (filename.endsWith(".opf")) {
          opfFile = filename;
          opfContent = await contents.files[filename].async("text");
          break;
        }
      }

      if (!opfFile) {
        throw new Error("Invalid EPUB: No OPF file found");
      }

      // Parse chapters from OPF
      const parser = new DOMParser();
      const doc = parser.parseFromString(opfContent, "application/xml");
      const spine = doc.querySelector("spine");
      const manifest = doc.querySelector("manifest");

      if (!spine || !manifest) {
        throw new Error("Invalid EPUB structure");
      }

      const items = {};
      manifest.querySelectorAll("item").forEach((item) => {
        items[item.getAttribute("id")] = item.getAttribute("href");
      });

      // Convert NodeList to Array and then map
      const itemrefs = Array.from(spine.querySelectorAll("itemref"));
      const chapterFiles = itemrefs.map((itemref) => {
        const id = itemref.getAttribute("idref");
        return items[id];
      });

      // Extract chapter contents
      const extractedChapters = [];
      for (const chapterFile of chapterFiles) {
        try {
          const chapterPath = opfFile
            .split("/")
            .slice(0, -1)
            .concat(chapterFile)
            .join("/");
          if (contents.files[chapterPath]) {
            const chapterContent = await contents.files[chapterPath].async(
              "text"
            );
            const chapterDoc = parser.parseFromString(
              chapterContent,
              "text/html"
            );
            const title =
              chapterDoc.querySelector("title")?.textContent ||
              `Chapter ${extractedChapters.length + 1}`;
            const body = chapterDoc.querySelector("body")?.textContent || "";
            const cleanText = body.trim().replace(/\s+/g, " ");

            if (cleanText.length > 0) {
              extractedChapters.push({
                id: extractedChapters.length,
                title,
                text: cleanText,
                characterCount: cleanText.length,
              });
            }
          }
        } catch (chapterError) {
          console.warn("Error parsing chapter:", chapterError);
          // Continue with next chapter instead of failing completely
          continue;
        }
      }

      if (extractedChapters.length === 0) {
        throw new Error("No readable chapters found in the EPUB file");
      }

      setChapters(extractedChapters);
      setSelectedChapters([]);
      setError("");
    } catch (error) {
      console.error("Error parsing EPUB:", error);
      setError(`Failed to parse EPUB file: ${error.message}`);
      if (chapters.length === 0) {
        setChapters([]);
        setSelectedChapters([]);
      }
    }
  };

  const handleChapterSelect = (chapterId) => {
    setSelectedChapters((prev) => {
      if (prev.includes(chapterId)) {
        return prev.filter((id) => id !== chapterId);
      } else {
        return [...prev, chapterId];
      }
    });
  };

  const handleChapterGenerate = async (chapter, generationType) => {
    if (isGenerating) return;

    try {
      setIsGenerating(true);
      setError("");
      setStatus("queued");
      setProgress(0);
      setMode(generationType);

      const endpoint =
        generationType === "video" ? "/generate" : "/generate-audio";
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, {
        text: chapter.text,
      });

      setJobId(response.data.job_id);
      jobIdRef.current = response.data.job_id;
      setMessage(`Starting ${generationType} generation for: ${chapter.title}`);
    } catch (error) {
      console.error("Generate error details:", error);
      setError(error.response?.data?.error || "Failed to start generation");
      setIsGenerating(false);
    }
  };

  const splitChapterIntoParts = (text, numParts) => {
    if (numParts <= 0) return [];
    const words = text.split(" ");
    const wordsPerPart = Math.ceil(words.length / numParts);
    const parts = [];

    for (let i = 0; i < numParts; i++) {
      const start = i * wordsPerPart;
      const end = Math.min(start + wordsPerPart, words.length);
      const partText = words.slice(start, end).join(" ");
      parts.push({
        text: partText,
        characterCount: partText.length,
      });
    }

    return parts;
  };

  const handleChapterPartsChange = (chapterId, numParts) => {
    const chapter = chapters.find((c) => c.id === chapterId);
    if (!chapter) return;

    setChapterPartsCount((prev) => ({
      ...prev,
      [chapterId]: numParts,
    }));

    const parts = splitChapterIntoParts(chapter.text, numParts);
    setChapterParts((prev) => ({
      ...prev,
      [chapterId]: parts,
    }));
  };

  const handlePartGenerate = async (chapterId, partIndex, generationType) => {
    if (isGenerating) return;
    const parts = chapterId ? chapterParts[chapterId] : null;
    if (chapterId && (!parts || !parts[partIndex])) return;

    try {
      setIsGenerating(true);
      setError("");
      setStatus("queued");
      setProgress(0);
      setCurrentPart(partIndex);
      setMode(generationType);

      const endpoint =
        generationType === "video" ? "/generate" : "/generate-audio";
      const textPayload = chapterId && parts ? parts[partIndex].text : text; // for non-chapter parts use main text

      const response = await axios.post(`${API_BASE_URL}${endpoint}`, {
        text: textPayload,
      });

      setJobId(response.data.job_id);
      jobIdRef.current = response.data.job_id;
      if (chapterId) {
        const chapter = chapters.find((c) => c.id === chapterId);
        setMessage(
          `Starting ${generationType} generation for Chapter ${
            chapter?.title
          } - Part ${partIndex + 1} of ${parts.length}`
        );
      } else {
        setMessage(`Starting ${generationType} generation`);
      }
    } catch (error) {
      console.error("Generate error details:", error);
      setError(error.response?.data?.error || "Failed to start generation");
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    try {
      const currentJobId = jobIdRef.current;
      const statusEndpoint = `${API_BASE_URL}${
        mode === "video" ? "/status" : "/audio-status"
      }/${currentJobId}`;
      const statusResponse = await axios.get(statusEndpoint);

      if (statusResponse.data.status !== "completed") {
        setError(
          `${
            mode === "video" ? "Video" : "Audio"
          } is not ready for download yet. Please wait for the generation to complete.`
        );
        return;
      }

      const downloadEndpoint = `${API_BASE_URL}${
        mode === "video" ? "/download" : "/download-audio"
      }/${currentJobId}`;
      const response = await axios.get(downloadEndpoint, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      const extension = mode === "video" ? "mp4" : "wav";
      link.setAttribute(
        "download",
        `generated_${mode}_${currentJobId}.${extension}`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      if (err.response?.status === 404) {
        setError(
          `${
            mode === "video" ? "Video" : "Audio"
          } file not found. Please try generating again.`
        );
      } else if (err.response?.status === 400) {
        setError(
          `${
            mode === "video" ? "Video" : "Audio"
          } is not ready for download yet. Please wait for the generation to complete.`
        );
      } else {
        setError("Error downloading: " + err.message);
      }
    }
  };

  const generateStory = async () => {
    if (!text) return;

    setIsGeneratingStory(true);
    setError(null);

    const lengthTokens = {
      short: 500,
      medium: 1000,
      long: 2000,
    };

    try {
      const response = await axios.post(
        "https://api.openai.com/v1/chat/completions",
        {
          model: "gpt-4",
          messages: [
            {
              role: "system",
              content:
                "You are a creative story writer. Generate an engaging story based on the given description. Make sure it has a well defined end that provides closure to the story.",
            },
            {
              role: "user",
              content: `Generate a ${storyLength} story based on this description: ${text}. Make it engaging and descriptive.`,
            },
          ],
          max_tokens: lengthTokens[storyLength],
          temperature: 0.8,
        },
        {
          headers: {
            Authorization: `Bearer ${OPENAI_API_KEY}`,
            "Content-Type": "application/json",
          },
        }
      );

      setText(response.data.choices[0].message.content);
    } catch (err) {
      console.error(
        "Story generation error:",
        err.response?.data || err.message
      );
      setError(
        err.response?.data?.error?.message ||
          "Failed to generate story. Please try again."
      );
    } finally {
      setIsGeneratingStory(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="container">
      <div className="header">
        <img src={logo} alt="Logo" className="logo" />
      </div>

      <div className="mode-toggle">
        <button
          className={`mode-btn ${mode === "video" ? "active" : ""}`}
          onClick={() => setMode("video")}
          disabled={isGenerating}
        >
          Video
        </button>
        <button
          className={`mode-btn ${mode === "audio" ? "active" : ""}`}
          onClick={() => setMode("audio")}
          disabled={isGenerating}
        >
          Audio
        </button>
        <button
          className={`mode-btn ${mode === "book" ? "active" : ""}`}
          onClick={() => setMode("book")}
          disabled={isGenerating}
        >
          Book
        </button>
      </div>

      <div className="story-controls">
        <select
          value={storyLength}
          onChange={(e) => setStoryLength(e.target.value)}
          className="length-select"
        >
          <option value="short">Short Story</option>
          <option value="medium">Medium Story</option>
          <option value="long">Long Story</option>
        </select>

        <button
          className="generate-story-btn"
          onClick={generateStory}
          disabled={!text || isGeneratingStory}
        >
          {isGeneratingStory ? "Generating..." : "Generate Story"}
        </button>

        <button className="copy-btn" onClick={copyToClipboard} disabled={!text}>
          Copy Text
        </button>
      </div>

      {mode !== "book" ? (
        <>
          <textarea
            value={text}
            onChange={handleTextChange}
            placeholder="Type something, and we'll turn it into voice magic!"
            disabled={isGenerating}
          />

          {parts.length > 0 ? (
            <div className="parts-container">
              <div className="parts-info">
                Text will be generated in {parts.length} parts (
                {CHAR_LIMIT.toLocaleString()} characters per part)
              </div>
              <div className="parts-list">
                {parts.map((part, index) => (
                  <div key={index} className="part-item">
                    <div className="part-header">
                      <span className="part-title">Part {index + 1}</span>
                      <span className="character-count">
                        ({part.length.toLocaleString()} characters)
                      </span>
                    </div>
                    <div className="part-preview">{part.slice(0, 100)}...</div>
                    <button
                      onClick={() => handlePartGenerate(null, index, mode)}
                      disabled={isGenerating}
                      className="generate-btn"
                    >
                      {isGenerating && currentPart === index
                        ? "Generating..."
                        : `Generate ${mode === "video" ? "Video" : "Audio"}`}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!text || isGenerating}
              className="generate-btn"
            >
              {isGenerating
                ? "Generating..."
                : `Generate ${mode === "video" ? "Video" : "Audio"}`}
            </button>
          )}
        </>
      ) : (
        <div className="book-upload">
          <div
            className="upload-area"
            onClick={() => document.getElementById("file-input").click()}
          >
            <input
              type="file"
              id="file-input"
              className="file-input"
              accept=".epub"
              onChange={handleFileUpload}
            />
            <label className="file-label">
              {bookName || "Click to upload EPUB file"}
            </label>
          </div>

          {chapters.length > 0 && (
            <div className="chapters-list">
              <h3>Chapters</h3>
              {chapters.map((chapter) => (
                <div key={chapter.id} className="chapter-container">
                  <div className="chapter-title">
                    <input
                      type="checkbox"
                      checked={selectedChapters.includes(chapter.id)}
                      onChange={() => handleChapterSelect(chapter.id)}
                    />
                    <span>{chapter.title}</span>
                    <span className="character-count">
                      ({chapter.characterCount.toLocaleString()} characters)
                    </span>
                  </div>
                  <div className="chapter-controls">
                    <div className="parts-control">
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={chapterPartsCount[chapter.id] || 1}
                        onChange={(e) =>
                          handleChapterPartsChange(
                            chapter.id,
                            parseInt(e.target.value) || 1
                          )
                        }
                        className="parts-input"
                        title="Number of parts to split this chapter into"
                      />
                      <label>parts</label>
                    </div>
                    {!chapterParts[chapter.id] ? (
                      <div className="chapter-actions">
                        <button
                          onClick={() =>
                            handleChapterGenerate(chapter, "video")
                          }
                          disabled={isGenerating}
                          className="generate-btn video-btn"
                        >
                          {isGenerating ? (
                            "Generating..."
                          ) : (
                            <>
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                                className="action-icon"
                              >
                                <path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm14.5 5.5L12 15 6.5 9.5l1-1L12 13l4.5-4.5 1 1z" />
                              </svg>
                              Generate Video
                            </>
                          )}
                        </button>
                        <button
                          onClick={() =>
                            handleChapterGenerate(chapter, "audio")
                          }
                          disabled={isGenerating}
                          className="generate-btn audio-btn"
                        >
                          {isGenerating ? (
                            "Generating..."
                          ) : (
                            <>
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                                className="action-icon"
                              >
                                <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 001.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.561.276 2.561-1.06V4.06zM18.584 5.106a.75.75 0 011.06 0c3.808 3.807 3.808 9.98 0 13.788a.75.75 0 11-1.06-1.06 8.25 8.25 0 000-11.668.75.75 0 010-1.06z" />
                                <path d="M15.932 7.757a.75.75 0 011.061 0 6 6 0 010 8.486.75.75 0 01-1.06-1.061 4.5 4.5 0 000-6.364.75.75 0 010-1.06z" />
                              </svg>
                              Generate Audio
                            </>
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="parts-list">
                        {chapterParts[chapter.id].map((part, index) => (
                          <div key={index} className="part-item">
                            <div className="part-header">
                              <span className="part-title">
                                Part {index + 1}
                              </span>
                              <span className="character-count">
                                ({part.characterCount.toLocaleString()}{" "}
                                characters)
                              </span>
                            </div>
                            <div className="part-preview">
                              {part.text.slice(0, 100)}...
                            </div>
                            <div className="part-actions">
                              <button
                                onClick={() =>
                                  handlePartGenerate(chapter.id, index, "video")
                                }
                                disabled={isGenerating}
                                className="generate-btn video-btn"
                              >
                                {isGenerating && currentPart === index ? (
                                  "Generating..."
                                ) : (
                                  <>
                                    <svg
                                      xmlns="http://www.w3.org/2000/svg"
                                      viewBox="0 0 24 24"
                                      fill="currentColor"
                                      className="action-icon"
                                    >
                                      <path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm14.5 5.5L12 15 6.5 9.5l1-1L12 13l4.5-4.5 1 1z" />
                                    </svg>
                                    Generate Video
                                  </>
                                )}
                              </button>
                              <button
                                onClick={() =>
                                  handlePartGenerate(chapter.id, index, "audio")
                                }
                                disabled={isGenerating}
                                className="generate-btn audio-btn"
                              >
                                {isGenerating && currentPart === index ? (
                                  "Generating..."
                                ) : (
                                  <>
                                    <svg
                                      xmlns="http://www.w3.org/2000/svg"
                                      viewBox="0 0 24 24"
                                      fill="currentColor"
                                      className="action-icon"
                                    >
                                      <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 001.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.561.276 2.561-1.06V4.06zM18.584 5.106a.75.75 0 011.06 0c3.808 3.807 3.808 9.98 0 13.788a.75.75 0 11-1.06-1.06 8.25 8.25 0 000-11.668.75.75 0 010-1.06z" />
                                      <path d="M15.932 7.757a.75.75 0 011.061 0 6 6 0 010 8.486.75.75 0 01-1.06-1.061 4.5 4.5 0 000-6.364.75.75 0 010-1.06z" />
                                    </svg>
                                    Generate Audio
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {(status || isGenerating) && (
        <div className="status">
          <div className="status-message">
            {message || getDefaultMessage(status, progress)}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="progress-text">{progress}% Complete</div>

          {status === "completed" && progress === 100 && (
            <div className="result-container">
              {mode === "video" ? (
                <>
                  <div className="video-preview">
                    <video
                      controls
                      autoPlay
                      playsInline
                      src={`${API_BASE_URL}/download/${jobIdRef.current}`}
                      className="video-player"
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                  <div className="video-actions">
                    <button
                      onClick={handleDownload}
                      className="video-action-btn"
                      title="Download video"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M12 15.575c-.183 0-.36-.072-.49-.203l-4.575-4.575c-.27-.27-.27-.71 0-.98s.71-.27.98 0L12 13.902l4.085-4.085c.27-.27.71-.27.98 0s.27.71 0 .98l-4.575 4.575c-.13.13-.307.203-.49.203zM12 20.575c-.414 0-.75-.336-.75-.75v-9.5c0-.414.336-.75.75-.75s.75.336.75.75v9.5c0 .414-.336.75-.75.75z" />
                      </svg>
                      Download
                    </button>
                    <button
                      onClick={() => {
                        const video = document.querySelector(".video-player");
                        if (video) {
                          video.requestFullscreen();
                        }
                      }}
                      className="video-action-btn"
                      title="Enter fullscreen"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9M20.25 20.25v-4.5m0 4.5h-4.5m4.5 0L15 15" />
                      </svg>
                      Fullscreen
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="audio-preview">
                    <audio
                      controls
                      autoPlay
                      src={`${API_BASE_URL}/${
                        mode === "audio" ? "download-audio" : "download-book"
                      }/${jobIdRef.current}`}
                      className="audio-player"
                    >
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                  <div className="audio-actions">
                    <button
                      onClick={handleDownload}
                      className="video-action-btn"
                      title={`Download ${
                        mode === "audio" ? "audio" : "audiobook"
                      }`}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M12 15.575c-.183 0-.36-.072-.49-.203l-4.575-4.575c-.27-.27-.27-.71 0-.98s.71-.27.98 0L12 13.902l4.085-4.085c.27-.27.71-.27.98 0s.27.71 0 .98l-4.575 4.575c-.13.13-.307.203-.49.203zM12 20.575c-.414 0-.75-.336-.75-.75v-9.5c0-.414.336-.75.75-.75s.75.336.75.75v9.5c0 .414-.336.75-.75.75z" />
                      </svg>
                      Download {mode === "audio" ? "Audio" : "Audiobook"}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
