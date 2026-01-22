// src/FileUpload.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // Import the CSS styles

const FileUpload = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const onUpload = async () => {
    if (!file) {
      setError("Please choose a file to upload.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Send the file to FastAPI (make sure FastAPI is running at the correct URL)
      const response = await axios.post("http://127.0.0.1:8000/extract-data/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      // Set the result from the response
      setResult(response.data);
    } catch (err) {
      setError("Error uploading file: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="App-header">
        <h1>Upload a Document to Extract Information</h1>
        <input type="file" onChange={onFileChange} />
        <button onClick={onUpload} disabled={loading}>
          {loading ? "Uploading..." : "Upload File"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result">
          <h2>Extracted Information:</h2>
          <p><strong>Name:</strong> {result.name}</p>
          <p><strong>Phone Number:</strong> {result.phone_number}</p>
          <p><strong>Email:</strong> {result.email}</p>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
