# Login Authentication System (Client-side)

Simple demo of registration, login, and a protected dashboard using localStorage and SHA-256 hashing via the Web Crypto API.

Files created:
- index.html — Login page
- register.html — Registration page
- dashboard.html — Protected page (requires login)
- css/style.css — Basic styles
- js/auth.js — Shared auth logic (hashing, register, login, session)

How to run:
1. Open `index.html` or `register.html` in your browser (double-click or use "Open File").
2. Register a new account, then login.

Notes:
- Passwords are hashed client-side with SHA-256 before storage (demo only). For production use, a server-side solution with bcrypt and secure sessions is required.
