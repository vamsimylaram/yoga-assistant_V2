import { useState, useEffect, useRef } from "react";
import "./App.css";
import assets from "./assets/assets";
import Auth from "../pages/Auth"; 

const defaultConfig = {
  bot_name: "Specialized Visual Assistant",
  welcome_message: "Hello! How can I help you with the yoga pose?",
  user_name: "You",
};

export default function App() {
  const [user, setUser] = useState(null);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // --- NEW: Chat History State ---
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);

  // --- Existing Chat State ---
  const [messages, setMessages] = useState([
    { sender: "bot", text: defaultConfig.welcome_message },
  ]);
  const [message, setMessage] = useState("");
  const [selectedImage, setSelectedImage] = useState(null);
  const [isTyping, setIsTyping] = useState(false);

  // Check for logged-in user on page load
  useEffect(() => {
    const savedUser = localStorage.getItem("yogaUser");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // --- NEW: Fetch Sidebar History when User Logs In ---
  useEffect(() => {
    if (user) {
      fetchSidebarHistory();
    }
  }, [user]);

  const fetchSidebarHistory = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/chats/${user.email}`);
      if (response.ok) {
        const data = await response.json();
        setChatHistory(data);
      }
    } catch (error) {
      console.error("Error fetching chat history:", error);
    }
  };

  // --- NEW: Load a Specific Chat ---
  const loadChat = async (chatId) => {
    try {
      const response = await fetch(`http://localhost:5000/api/chat/${chatId}`);
      if (response.ok) {
        const data = await response.json();
        setCurrentChatId(data.chat_id);
        
        // Format messages for the UI
        const loadedMessages = data.messages.map(msg => ({
          sender: msg.sender,
          text: msg.text,
          image_url: msg.image_url // Now handles Cloudinary URLs!
        }));
        
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error("Error loading chat:", error);
    }
  };

  // --- NEW: Start a New Chat ---
  const startNewChat = () => {
    setCurrentChatId(null);
    setMessages([{ sender: "bot", text: defaultConfig.welcome_message }]);
    setMessage("");
    setSelectedImage(null);
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    localStorage.setItem("yogaUser", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    setChatHistory([]);
    setCurrentChatId(null);
    localStorage.removeItem("yogaUser");
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();   

    if (!message.trim() && !selectedImage) return;

    const currentPrompt = message;
    const currentImageBase64 = selectedImage?.data || null;

    // Add user message to UI immediately
    setMessages(prev => [
      ...prev,
      { sender: "user", text: currentPrompt, image: selectedImage }
    ]);

    setMessage("");
    setSelectedImage(null);
    setIsTyping(true);

    try {
      // ➡️ UPDATED: Direct fetch call with email and chat_id
      const response = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: currentPrompt,
          image_data: currentImageBase64,
          email: user.email,
          chat_id: currentChatId // Pass null if new chat, or ID if existing
        })
      });

      const data = await response.json();

      if (response.ok) {
        setMessages(prev => [
          ...prev,
          { sender: "bot", text: data.answer }
        ]);

        // If this was a new chat, the backend just created it.
        // Save the new ID and refresh the sidebar so the title appears!
        if (!currentChatId && data.chat_id) {
          setCurrentChatId(data.chat_id);
          fetchSidebarHistory(); 
        }
      } else {
        throw new Error(data.error || "Server error");
      }
    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [
        ...prev,
        { sender: "bot", text: "Server error. Try again." }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return; 

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setSelectedImage({
          data: event.target.result,
          name: file.name,
          type: file.type,
        });
      };
      reader.readAsDataURL(file);
    }
    e.target.value = ""; 
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); 
      handleSend(e);      
    }
  };

  if (!user) {
    return <Auth onLogin={handleLoginSuccess} />;
  }

  return (
    // ➡️ CHANGED: Added app-layout wrapper for the sidebar
    <div className="app-layout">
      
      {/* --- NEW: Sidebar Section --- */}
      <aside className="sidebar">
        <button className="new-chat-btn" onClick={startNewChat}>
          + New Chat
        </button>
        <div className="chat-history-list">
          {chatHistory.map((chat) => (
            <div 
              key={chat.id} 
              className={`history-item ${currentChatId === chat.id ? 'active' : ''}`}
              onClick={() => loadChat(chat.id)}
            >
              💬 {chat.title}
            </div>
          ))}
        </div>
      </aside>

      {/* --- Existing Chat Container --- */}
      <main className="chat-container">
        <header className="chat-header">
          <div className="header-left">
              <h1>{defaultConfig.bot_name}</h1>
              <p>Online • Ready to help</p>
          </div>
          <div className="header-right" style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
              <span style={{fontSize: '14px', color: '#fff'}}>Hi, {user.name}</span>
              <button 
                  onClick={handleLogout} 
                  style={{
                      padding: '5px 10px', 
                      fontSize: '12px', 
                      borderRadius: '15px', 
                      border: 'none', 
                      cursor: 'pointer',
                      background: '#ff4b2b',
                      color: 'white'
                  }}
              >
                  Logout
              </button>
          </div>
        </header>

        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.sender}`}>
              <div className="message-avatar">
                {msg.sender === "bot" ? "🤖" : defaultConfig.user_name.charAt(0)}
              </div>
              <div className="message-bubble">
                
                {/* ➡️ CHANGED: Render Cloudinary URL if it exists, otherwise local preview */}
                {(msg.image_url || msg.image) && (
                  <img 
                    src={msg.image_url || msg.image.data} 
                    alt="Pose" 
                    className="message-image" 
                    style={{ maxWidth: '100%', borderRadius: '8px', marginBottom: '8px' }}
                  />
                )}

                {msg.text && <div>{msg.text}</div>}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="typing-indicator show">
              <div className="message-avatar">🤖</div>
              <div className="typing-dots">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef}></div>
        </div>

        <div className="chat-input-container" style={{ position: 'relative' }}>
          
          {selectedImage && (
            <div 
              className="image-preview-container show" 
              style={{
                position: 'absolute',
                bottom: '100%', 
                left: '10px',
                marginBottom: '10px',
                backgroundColor: '#fff',
                padding: '8px',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                zIndex: 50
              }}
            >
              <img 
                className="image-preview" 
                src={selectedImage.data} 
                alt="Preview" 
                style={{ maxHeight: '80px', borderRadius: '4px' }}
              />
              <div className="image-preview-controls" style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '5px' }}>
                <span className="image-preview-name" style={{ fontSize: '11px', color: '#666', maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedImage.name}
                </span>
                <button type="button" onClick={() => setSelectedImage(null)} style={{ background: '#ff4b2b', color: '#fff', border: 'none', borderRadius: '4px', padding: '2px 6px', fontSize: '11px', cursor: 'pointer' }}>
                  Remove
                </button>
              </div>
            </div>
          )}

          <form className="chat-input-form" onSubmit={handleSend}>
            <div className="input-container">
              <textarea
                className="chat-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown} 
                placeholder="Type your message..."
                rows="1"
              ></textarea>

              <label className="image-upload-btn" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                <img
                  src={assets.gallery_icon}
                  alt="Send Image"
                  style={{ filter: 'brightness(0) invert(1)', width: '20px', height: '20px' }} 
                />
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleImageUpload} 
                  style={{ display: 'none' }} 
                />
              </label>
            </div>

            <button type="submit" className="send-button">➤</button>
          </form>
        </div>
      </main>
    </div>
  );
}
