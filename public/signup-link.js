// MedDesk AI - Add Signup Link to Login Page
(function() {
    function addSignupLink() {
        // Look for the sign in button area
        var buttons = document.querySelectorAll('button');
        var signInBtn = null;
        buttons.forEach(function(b) {
            if (b.textContent.trim().toLowerCase().includes('sign in')) {
                signInBtn = b;
            }
        });
        
        if (!signInBtn) return false;
        
        // Check if link already added
        if (document.getElementById('meddesk-signup-link')) return true;
        
        // Create signup link
        var container = signInBtn.closest('.MuiStack-root') || signInBtn.closest('form') || signInBtn.parentElement;
        if (!container) return false;
        
        var wrapper = document.createElement('div');
        wrapper.id = 'meddesk-signup-link';
        wrapper.style.cssText = 'text-align:center;margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1);';
        wrapper.innerHTML = '<span style="color:#888;font-size:14px;">Don\'t have an account? </span><a href="/auth/signup" style="color:#4a9eff;text-decoration:none;font-weight:600;font-size:14px;">Sign Up</a>';
        
        container.parentElement.insertBefore(wrapper, container.nextSibling);
        return true;
    }
    
    // Try immediately, then retry
    if (!addSignupLink()) {
        var attempts = 0;
        var interval = setInterval(function() {
            attempts++;
            if (addSignupLink() || attempts > 20) {
                clearInterval(interval);
            }
        }, 500);
    }
})();
