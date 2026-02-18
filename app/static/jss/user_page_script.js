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
    loginModal.style.display = 'block';
    signupModal.style.display = 'none';
}

// Open Signup Modal
function openSignupModal() {
    signupModal.style.display = 'block';
    loginModal.style.display = 'none';
}

// Close modals
function closeAllModals() {
    loginModal.style.display = 'none';
    signupModal.style.display = 'none';
}

// Event listeners for opening modals
navLoginBtn.addEventListener('click', openLoginModal);
navSignupBtn.addEventListener('click', openSignupModal);
getStartedBtn.addEventListener('click', openSignupModal);

// Event listeners for close buttons
closeButtons.forEach(btn => {
    btn.addEventListener('click', closeAllModals);
});

// Toggle between login and signup
toggleSignupLink.addEventListener('click', (e) => {
    e.preventDefault();
    openSignupModal();
});

toggleLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    openLoginModal();
});

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === loginModal) {
        closeAllModals();
    }
    if (e.target === signupModal) {
        closeAllModals();
    }
});

// Handle Login Form Submission
loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = loginForm.querySelector('input[type="text"]').value;
    const password = loginForm.querySelector('input[type="password"]').value;
    
    if (email && password) {
        console.log('Login attempt:', { email, password });
        alert('Login successful! (Demo mode)');
        closeAllModals();
        loginForm.reset();
    }
});

// Handle Signup Form Submission
signupForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const fullName = signupForm.querySelectorAll('input')[0].value;
    const email = signupForm.querySelectorAll('input')[1].value;
    const password1 = signupForm.querySelectorAll('input')[2].value;
    const password2 = signupForm.querySelectorAll('input')[3].value;
    
    if (password1 !== password2) {
        alert('Passwords do not match!');
        return;
    }
    
    if (fullName && email && password1) {
        console.log('Signup attempt:', { fullName, email });
        alert('Account created successfully! (Demo mode)');
        closeAllModals();
        signupForm.reset();
    }
});

// Learn More Button (Placeholder)
learnMoreBtn.addEventListener('click', () => {
    alert('Explore our features section to learn more about SmartFlow!');
});

// Smooth scroll for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const element = document.querySelector(href);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

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
