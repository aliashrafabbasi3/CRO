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
    setError(null);
    setResult(null);
  };

  const onUpload = async () => {
    if (!file) {
      setError("Please choose a file to upload.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

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
      <div className="upload-container">
        <div className="App-header">
          <h1>✨ Document Data Extractor</h1>
        </div>

        <div className="file-input-wrapper">
          <input type="file" onChange={onFileChange} accept="image/*,.pdf" />
        </div>

        <button onClick={onUpload} disabled={loading}>
          {loading ? (
            <>
              Processing
              <span className="loading-spinner"></span>
            </>
          ) : (
            "🚀 Extract Information"
          )}
        </button>

        {error && <div className="error">❌ {error}</div>}
      </div>

      {result && (
        <div className="result">
          <h2>📋 Extracted Information</h2>
          <div className="result-item">
            <strong>🏢 Facility Name:</strong>
            <span> {result.fields?.facility_name || 'Not found'}</span>
          </div>
          <div className="result-item">
            <strong>👤 Person Name:</strong>
            <span> {result.fields?.person_name || 'Not found'}</span>
          </div>
          <div className="result-item">
            <strong>💼 Role:</strong>
            <span> {result.fields?.person_role || 'Not found'}</span>
          </div>
          <div className="result-item">
            <strong>📧 Email:</strong>
            <span> {result.fields?.email || 'Not found'}</span>
          </div>
          <div className="result-item">
            <strong>📱 Phone:</strong>
            <span> {result.fields?.phone || 'Not found'}</span>
          </div>
          <div className="result-item">
            <strong>📍 Address:</strong>
            <span> {result.fields?.address || 'Not found'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
