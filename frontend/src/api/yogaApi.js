// frontend/src/api/yogaApi.js
import axios from "axios";

// Base URL must match your Flask server
const API_BASE_URL = "http://localhost:5000";

/**
 * Calls the Flask backend to get a yoga pose recommendation/answer.
 * The backend expects JSON with optional Base64 image data.
 *
 * @param {string} query - The user's text message.
 * @param {object | null} image - The selected image object (data, name, type).
 * @returns {Promise<string>} The answer string from the backend.
 */
export const getYogaRecommendation = async (query, image) => {
  // Prepare JSON payload that matches Flask backend
  const payload = {
    query: query || "",
    image_data: image ? image.data : null,
  };

  try {
    // Send JSON payload to Flask backend
    const response = await axios.post(`${API_BASE_URL}/api/chat`, payload, {
      headers: { "Content-Type": "application/json" },
    });

    // Extract and return the "answer" field from Flask response
    return response.data.answer;
  } catch (error) {
    console.error("Error fetching recommendation from backend:", error);

    let errorMessage = "Could not connect to the Yoga Assistant backend.";
    if (error.response) {
      errorMessage = `Backend Error: ${error.response.status} - ${
        error.response.data.error || "Server issue"
      }`;
    }

    throw new Error(errorMessage);
  }
};
