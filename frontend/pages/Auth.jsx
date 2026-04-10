import { useState } from "react";
import "./Auth.css";

const Auth = ({ onLogin }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [signInData, setSignInData] = useState({ email: "", password: "" });
  const [signUpData, setSignUpData] = useState({ name: "", email: "", password: "" });
  
  const [showSignInPassword, setShowSignInPassword] = useState(false);
  const [showSignUpPassword, setShowSignUpPassword] = useState(false);

  const handleSignInChange = (e) => {
    setSignInData({ ...signInData, [e.target.name]: e.target.value });
  };

  const handleSignUpChange = (e) => {
    setSignUpData({ ...signUpData, [e.target.name]: e.target.value });
  };

  const handleSignInSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:5000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signInData),
      });
      
      const data = await response.json();
      if (response.ok) {
        onLogin(data); 
      } else {
        alert(data.error);
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleSignUpSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:5000/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signUpData),
      });

      const data = await response.json();
      if (response.ok) {
        alert("Registration Successful! Please Sign In.");
        setIsSignUp(false);
      } else {
        alert(data.error);
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  // Helper function to render the Eye SVG
  const EyeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#888888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>
  );

  // Helper function to render the Eye-Off (Hidden) SVG
  const EyeOffIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#888888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    </svg>
  );

  return (
    <div className="auth-body">
      <div className={`container ${isSignUp ? "right-panel-active" : ""}`} id="container">
        
        {/* Sign Up Form */}
        <div className="form-container sign-up-container">
          <form onSubmit={handleSignUpSubmit}>
            <h1>Create Account</h1>
            <span>use your email for registration</span>
            <input type="text" name="name" placeholder="Name" value={signUpData.name} onChange={handleSignUpChange} required />
            <input type="email" name="email" placeholder="Email" value={signUpData.email} onChange={handleSignUpChange} required />
            
            <div className="password-container">
              <input 
                type={showSignUpPassword ? "text" : "password"} 
                name="password" 
                placeholder="Password" 
                value={signUpData.password} 
                onChange={handleSignUpChange} 
                required 
              />
              <span 
                className="password-toggle" 
                onClick={() => setShowSignUpPassword(!showSignUpPassword)}
                title={showSignUpPassword ? "Hide password" : "Show password"}
              >
                {showSignUpPassword ? <EyeOffIcon /> : <EyeIcon />}
              </span>
            </div>

            <button type="submit">Sign Up</button>
          </form>
        </div>

        {/* Sign In Form */}
        <div className="form-container sign-in-container">
          <form onSubmit={handleSignInSubmit}>
            <h1>Sign in</h1>
            <span>use your account</span>
            <input type="email" name="email" placeholder="Email" value={signInData.email} onChange={handleSignInChange} required />
            
            <div className="password-container">
              <input 
                type={showSignInPassword ? "text" : "password"} 
                name="password" 
                placeholder="Password" 
                value={signInData.password} 
                onChange={handleSignInChange} 
                required 
              />
              <span 
                className="password-toggle" 
                onClick={() => setShowSignInPassword(!showSignInPassword)}
                title={showSignInPassword ? "Hide password" : "Show password"}
              >
                {showSignInPassword ? <EyeOffIcon /> : <EyeIcon />}
              </span>
            </div>

            <a href="#">Forgot your password?</a>
            <button type="submit">Sign In</button>
          </form>
        </div>

        {/* Overlay */}
        <div className="overlay-container">
          <div className="overlay">
            <div className="overlay-panel overlay-left">
              <h1>Welcome Back!</h1>
              <p>To keep connected with us please login with your personal info</p>
              <button className="ghost" onClick={() => setIsSignUp(false)}>Sign In</button>
            </div>
            <div className="overlay-panel overlay-right">
              <h1>Hello, Friend!</h1>
              <p>Enter your personal details and start your journey with us</p>
              <button className="ghost" onClick={() => setIsSignUp(true)}>Sign Up</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Auth;