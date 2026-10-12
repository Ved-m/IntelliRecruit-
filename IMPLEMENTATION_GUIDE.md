# Job Recommendation System - Implementation Guide

## 🔐 STEP 1: FIREBASE AUTHENTICATION SETUP

### A. Firebase Console Configuration (5-10 minutes)

1. **Create Firebase Project**
   - Go to https://console.firebase.google.com/
   - Click "Create Project"
   - Name: `job-recommendation-system`
   - Enable Google Analytics (optional)

2. **Enable Authentication Methods**
   - Navigate to: **Authentication** > **Sign-in method**
   - Enable: **Email/Password** authentication
   - Enable: **Google** sign-in (for production)

3. **Get Service Account Key**
   - Go to: **Project Settings** (⚙️) > **Service Accounts**
   - Click **Generate New Private Key**
   - Save as `firebase-key.json` in your project root

4. **Get Firebase Config**
   - Go to: **Project Settings** > **General**
   - Copy your Firebase config values
   - Update `.env` file with these values

### B. Local Setup (10 minutes)

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Environment Variables**
   - Copy to `.env`:
   ```
   FIREBASE_API_KEY=your_firebase_api_key
   FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
   FIREBASE_DATABASE_URL=https://your_project.firebaseio.com
   FIREBASE_PROJECT_ID=your_project_id
   PINECONE_API_KEY=your_pinecone_key
   PINECONE_INDEX_NAME=job-recommendations
   ```

3. **Database Setup**
   - Open MySQL
   - Run:
   ```bash
   mysql -u root -p123456 < database.sql
   ```

### C. API Endpoints Reference

#### 📝 Authentication Endpoints

**Register User**
```
POST /api/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe",
  "role": "user"  // or "admin"
}

Response:
{
  "message": "User registered successfully",
  "firebase_uid": "abc123",
  "email": "user@example.com",
  "role": "user"
}
```

**Login (with Firebase Token)**
```
POST /api/login
Content-Type: application/json

{
  "idToken": "firebase_id_token_from_frontend"
}

Response:
{
  "message": "Login successful",
  "user_id": 1,
  "email": "user@example.com",
  "role": "user",
  "idToken": "token_here"
}
```

**Get User Profile**
```
GET /api/user-profile
Authorization: Bearer <idToken>

Response:
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "created_at": "2024-01-01T10:00:00"
}
```

#### 📋 Job Endpoints

**Get All Jobs**
```
GET /api/jobs
```

**Post Job (Admin Only)**
```
POST /api/admin/jobs
Authorization: Bearer <admin_idToken>
Content-Type: application/json

{
  "title": "Senior Software Engineer",
  "description": "Looking for experienced engineer with 5+ years..."
}
```

**Delete Job (Admin Only)**
```
DELETE /api/jobs/<job_id>
Authorization: Bearer <admin_idToken>
```

#### 📄 Application Endpoints

**Apply for Job (User)**
```
POST /api/apply-job
Authorization: Bearer <user_idToken>
Content-Type: multipart/form-data

form data:
- job_id: 1
- resume: <PDF file>
```

**Get My Applications**
```
GET /api/my-applications
Authorization: Bearer <user_idToken>

Response:
[
  {
    "id": 1,
    "title": "Software Engineer",
    "score": 85.50,
    "status": "pending",
    "review": null,
    "submitted_at": "2024-01-01T10:00:00"
  }
]
```

#### 👥 Admin Dashboard Endpoints

**Get Applicants for Specific Job (Job-wise Top K)**
```
GET /api/admin/job-applicants/<job_id>?top_k=10
Authorization: Bearer <admin_idToken>

Response:
[
  {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane@example.com",
    "score": 92.5,
    "status": "pending",
    "submitted_at": "2024-01-01T10:00:00"
  }
]
```

**Get All Jobs with Applicant Stats**
```
GET /api/admin/all-applicants
Authorization: Bearer <admin_idToken>

Response:
[
  {
    "job_id": 1,
    "title": "Senior Engineer",
    "total_applicants": 15,
    "reviewed": 5,
    "accepted": 2,
    "rejected": 1
  }
]
```

**Review Application (Update Status)**
```
POST /api/admin/review-application/<app_id>
Authorization: Bearer <admin_idToken>
Content-Type: application/json

{
  "status": "accepted",  // or "rejected", "reviewed", "pending"
  "review": "Great resume! Would like to interview..."
}
```

**Generate AI Review**
```
POST /api/admin/generate-review/<app_id>
Authorization: Bearer <admin_idToken>

Response:
{
  "review": "Generated AI review text here..."
}
```

---

## 📱 FRONTEND MODIFICATIONS NEEDED

### Create Firebase Authentication Module

Create `static/js/firebase-config.js`:
```javascript
// Import Firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.0.0/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.0.0/firebase-auth.js";

// Your Firebase config
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "your_project.firebaseapp.com",
  databaseURL: "https://your_project.firebaseio.com",
  projectId: "your_project_id",
  storageBucket: "your_project.appspot.com",
  messagingSenderId: "your_sender_id",
  appId: "your_app_id"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Register Function
async function registerUser(email, password, name, role = 'user') {
  try {
    // Create Firebase user
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Register in backend
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name, role })
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    
    return { success: true, data, idToken };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Login Function
async function loginUser(email, password) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Verify login in backend
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken })
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    
    // Store token
    localStorage.setItem('idToken', idToken);
    localStorage.setItem('user', JSON.stringify(data));
    
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Logout Function
function logoutUser() {
  auth.signOut();
  localStorage.removeItem('idToken');
  localStorage.removeItem('user');
}

// Get Current User
function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

// Get ID Token
function getIdToken() {
  return localStorage.getItem('idToken');
}

// Export functions
export { registerUser, loginUser, logoutUser, getCurrentUser, getIdToken, auth };
```

### Protected API Calls Helper

Create `static/js/api-client.js`:
```javascript
import { getIdToken } from './firebase-config.js';

async function apiCall(endpoint, method = 'GET', body = null) {
  const token = getIdToken();
  
  if (!token) {
    window.location.href = '/login';
    return;
  }
  
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };
  
  if (body) {
    options.body = JSON.stringify(body);
  }
  
  const response = await fetch(endpoint, options);
  
  if (response.status === 401) {
    localStorage.removeItem('idToken');
    window.location.href = '/login';
  }
  
  return response.json();
}

async function uploadFile(endpoint, file, additional_data = {}) {
  const token = getIdToken();
  const formData = new FormData();
  
  formData.append('resume', file);
  for (let key in additional_data) {
    formData.append(key, additional_data[key]);
  }
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
}

export { apiCall, uploadFile };
```

---

## 🎯 STEP 2: PINECONE SETUP

1. **Create Pinecone Account**
   - Go to https://www.pinecone.io/
   - Sign up and create account
   - Create index: `job-recommendations`
   - Dimension: `384` (for all-MiniLM-L6-v2 model)
   - Metric: `cosine`

2. **Get API Key**
   - Copy API key from dashboard
   - Add to `.env`: `PINECONE_API_KEY=your_key`

---

## 🎯 STEP 3: MIGRATION STEPS

### Replace app.py with app_new.py
```bash
# Backup old file
move app.py app_old.py

# Use new file
move app_new.py app.py
```

### Run Application
```bash
pip install -r requirements.txt
python app.py
```

---

## ✅ TESTING CHECKLIST

- [ ] Register new user (user role)
- [ ] Register admin user (admin role)
- [ ] Login as user
- [ ] Admin posts a job
- [ ] User applies for job
- [ ] Admin sees job-wise applicants (not all)
- [ ] User sees their application status
- [ ] Admin generates AI review
- [ ] User sees the review on dashboard
- [ ] Delete job removes vectors from Pinecone
- [ ] Logout/Login maintains role separation

---

## 🐛 TROUBLESHOOTING

**Firebase Key Error:**
```
Make sure firebase-key.json is in project root
Check Project ID matches .env FIREBASE_PROJECT_ID
```

**Pinecone Connection Error:**
```
Verify PINECONE_API_KEY in .env
Check index name matches PINECONE_INDEX_NAME
```

**Database Error:**
```
Run: mysql -u root -p123456 < database.sql
Verify users table has firebase_uid field
```

---

## 📊 Database Schema Changes

**New Fields:**
- users.firebase_uid (unique identifier)
- users.role (enum: user, admin)
- applications.status (enum: pending, reviewed, accepted, rejected)
- applications.review (AI-generated text)
- applications.reviewed_by (admin user_id)

**Removed Fields:**
- vector (moved to Pinecone)

---

Done! You now have:
✅ Firebase Authentication (separate user/admin)
✅ Pinecone Vector Storage
✅ Job-wise Top K Applicants
✅ User Application Status Dashboard
✅ AI Review Generation
