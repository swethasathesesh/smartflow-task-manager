const loginModal = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');

// Get button elements
const getStartedBtn = document.getElementById('getStartedBtn');
const learnMoreBtn = document.getElementById('learnMoreBtn');
const navLoginBtn = document.getElementById('navLoginBtn');
const navSignupBtn = document.getElementById('navSignupBtn');
const toggleSignupLink = document.getElementById('toggleSignup');
const toggleLoginLink = document.getElementById('toggleLogin');

// Get close buttons
const closeButtons = document.querySelectorAll('.close');

// Open Login Modal
function openLoginModal() {
    if (loginModal) loginModal.style.display = 'block';
    if (signupModal) signupModal.style.display = 'none';
}

// Open Signup Modal
function openSignupModal() {
    if (signupModal) signupModal.style.display = 'block';
    if (loginModal) loginModal.style.display = 'none';
}

// Close modals
function closeAllModals() {
    if (loginModal) loginModal.style.display = 'none';
    if (signupModal) signupModal.style.display = 'none';
}

// Event listeners for opening modals (Polite versions!)
if (navLoginBtn) navLoginBtn.addEventListener('click', openLoginModal);
if (navSignupBtn) navSignupBtn.addEventListener('click', openSignupModal);
if (getStartedBtn) getStartedBtn.addEventListener('click', openSignupModal);

// Event listeners for close buttons
closeButtons.forEach(btn => {
    btn.addEventListener('click', closeAllModals);
});

// Toggle between login and signup
if (toggleSignupLink) {
    toggleSignupLink.addEventListener('click', (e) => {
        e.preventDefault();
        openSignupModal();
    });
}

if (toggleLoginLink) {
    toggleLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        openLoginModal();
    });
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === loginModal) {
        closeAllModals();
    }
    if (e.target === signupModal) {
        closeAllModals();
    }
});

// Handle Login Form Submission (Demo)
if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const emailInput = loginForm.querySelector('input[type="text"]') || loginForm.querySelector('input[type="email"]');
        const passwordInput = loginForm.querySelector('input[type="password"]');
        
        const email = emailInput ? emailInput.value : '';
        const password = passwordInput ? passwordInput.value : '';
        
        if (email && password) {
            console.log('Login attempt:', { email, password });
            alert('Login successful! (Demo mode)');
            closeAllModals();
            loginForm.reset();
        }
    });
}

// --- REAL BACKEND CONNECTION FOR SIGN UP ---
if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
        // 1. Stop page reload
        e.preventDefault();

        // 2. Grab the text from the inputs using their IDs
        const nameValue = document.getElementById("fullName").value;
        const emailValue = document.getElementById("signupEmail").value;
        const passwordValue = document.getElementById("signupPassword").value;
        const confirmPasswordValue = document.getElementById("confirmPassword").value;
        
        // 3. Password match check
        if (passwordValue !== confirmPasswordValue) {
            alert('Passwords do not match. Please try again.');
            return;
        }
        
        // 4. Package for Python
        const userData = {
            full_name: nameValue,
            email: emailValue,
            password: passwordValue
        };

        try {
            // 5. Send to our specific FastAPI backend route
            const response = await fetch("http://127.0.0.1:8000/signup", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                alert("✅ Account created successfully! You can now log in.");
                signupForm.reset(); 
                if (toggleLoginLink) toggleLoginLink.click(); // Flips back to login screen
            } else {
                const errorData = await response.json();
                alert("❌ Sign Up Failed: " + JSON.stringify(errorData.detail));
            }
        } catch (error) {
            console.error("Connection error:", error);
            alert("Server is offline or unreachable.");
        }
    });
}

// Learn More Button (Placeholder)
if (learnMoreBtn) {
    learnMoreBtn.addEventListener('click', () => {
        alert('Explore our features section to learn more about SmartFlow!');
    });
}

// Add ripple effect to buttons
function addRippleEffect(element) {
    element.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    });
}

// Apply ripple effect to all buttons
document.querySelectorAll('.btn, .nav-btn, .form-btn').forEach(button => {
    addRippleEffect(button);
});