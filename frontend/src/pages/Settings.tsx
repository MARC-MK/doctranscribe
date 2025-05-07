import React, { useState } from "react";
import { Settings as SettingsIcon, Save, Image, Eye, FileText, AlertCircle } from "lucide-react";

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    confidenceThreshold: 80,
    autoDownload: true,
    retentionPeriod: "30",
    emailNotifications: true,
    theme: "dark",
    ocrEngine: "standard",
    processInBackground: true
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings({
      ...settings,
      [name]: type === "checkbox" ? checked : value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real app, we would save the settings to the backend here
    alert("Settings saved successfully!");
  };

  return (
    <div className="max-w-4xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold mb-3 flex items-center gap-2">
          <SettingsIcon className="text-primary" /> Settings
        </h1>
        <p className="text-gray-400">
          Configure DocTranscribe to match your survey processing needs
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* OCR & AI Settings */}
        <section className="bg-background rounded-lg border border-background-light p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Eye className="text-primary" size={20} /> OCR & AI Settings
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="flex justify-between mb-2">
                <span>OCR Confidence Threshold</span>
                <span className="text-primary">{settings.confidenceThreshold}%</span>
              </label>
              <input
                type="range"
                name="confidenceThreshold"
                min="50"
                max="95"
                value={settings.confidenceThreshold}
                onChange={handleChange}
                className="w-full accent-primary bg-background-light h-2 rounded-full appearance-none cursor-pointer"
              />
              <p className="text-sm text-gray-400 mt-1">
                Responses below this confidence level will be flagged for review
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block mb-2">OCR Engine</label>
                <select
                  name="ocrEngine"
                  value={settings.ocrEngine}
                  onChange={handleChange}
                  className="w-full bg-background-light border border-background-light rounded p-2"
                >
                  <option value="standard">Standard (Faster, Good Accuracy)</option>
                  <option value="enhanced">Enhanced (Slower, Higher Accuracy)</option>
                  <option value="premium">Premium (Best for Difficult Handwriting)</option>
                </select>
              </div>
              
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="processInBackground"
                  name="processInBackground"
                  checked={settings.processInBackground}
                  onChange={handleChange}
                  className="mr-2 h-4 w-4 accent-primary"
                />
                <label htmlFor="processInBackground">
                  Process uploads in background
                </label>
              </div>
            </div>
          </div>
        </section>
        
        {/* Data Storage Settings */}
        <section className="bg-background rounded-lg border border-background-light p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <FileText className="text-primary" size={20} /> Data & Storage
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block mb-2">Data Retention Period</label>
              <select
                name="retentionPeriod"
                value={settings.retentionPeriod}
                onChange={handleChange}
                className="w-full bg-background-light border border-background-light rounded p-2"
              >
                <option value="7">7 Days</option>
                <option value="30">30 Days</option>
                <option value="90">90 Days</option>
                <option value="365">1 Year</option>
                <option value="0">Forever (Not Recommended)</option>
              </select>
              <p className="text-sm text-gray-400 mt-1">
                How long to keep your processed files on our servers
              </p>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="autoDownload"
                name="autoDownload"
                checked={settings.autoDownload}
                onChange={handleChange}
                className="mr-2 h-4 w-4 accent-primary"
              />
              <label htmlFor="autoDownload">
                Automatically download results when processing completes
              </label>
            </div>
          </div>
        </section>
        
        {/* Notification Settings */}
        <section className="bg-background rounded-lg border border-background-light p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="text-primary" size={20} /> Notifications
          </h2>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="emailNotifications"
              name="emailNotifications"
              checked={settings.emailNotifications}
              onChange={handleChange}
              className="mr-2 h-4 w-4 accent-primary"
            />
            <label htmlFor="emailNotifications">
              Receive email notifications when batch processing completes
            </label>
          </div>
        </section>
        
        {/* Theme Settings */}
        <section className="bg-background rounded-lg border border-background-light p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Image className="text-primary" size={20} /> Appearance
          </h2>
          
          <div>
            <label className="block mb-2">Theme</label>
            <div className="flex gap-4">
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="theme"
                  value="dark"
                  checked={settings.theme === "dark"}
                  onChange={handleChange}
                  className="mr-2 h-4 w-4 accent-primary"
                />
                Dark
              </label>
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="theme"
                  value="light"
                  checked={settings.theme === "light"}
                  onChange={handleChange}
                  className="mr-2 h-4 w-4 accent-primary"
                />
                Light (Coming Soon)
              </label>
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="theme"
                  value="system"
                  checked={settings.theme === "system"}
                  onChange={handleChange}
                  className="mr-2 h-4 w-4 accent-primary"
                />
                System (Coming Soon)
              </label>
            </div>
          </div>
        </section>
        
        <div className="flex justify-end">
          <button 
            type="submit" 
            className="px-6 py-3 bg-primary text-white rounded-lg flex items-center gap-2 hover:bg-primary/90 transition"
          >
            <Save size={18} /> Save Settings
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage; 