# 📊 ARCHITECTURE & FLOW DIAGRAMS

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User's Browser                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   User       │    │  Admin       │    │  Auth Page   │      │
│  │ Dashboard    │    │ Dashboard    │    │  Login/Reg   │      │
│  │              │    │              │    │              │      │
│  │ - View Jobs  │    │ - Post Jobs  │    │ - Firebase   │      │
│  │ - Apply      │    │ - View Apps  │    │   Auth       │      │
│  │ - See Status │    │ - Review     │    │              │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             │                                  │
│          Sends Token: Authorization: Bearer <Token>           │
│                             │                                  │
└─────────────────────────────┼──────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend (app.py)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  @app.route("/api/auth/...")      [Public Routes]       │  │
│  │  - /api/register                                         │  │
│  │  - /api/login                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  @token_required   [Protected - All Users]               │  │
│  │  - /api/jobs       ──► GET jobs list                     │  │
│  │  - /api/apply-job  ──► POST application + resume         │  │
│  │  - /api/my-apps    ──► GET user's applications          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  @admin_required   [Protected - Admin Only]              │  │
│  │  - /api/admin/jobs         ──► POST new job             │  │
│  │  - /api/admin/job-apps/<id>    ──► GET top K for job    │  │
│  │  - /api/admin/review-app   ──► POST review              │  │
│  │  - /api/admin/generate-review   ──► AI review           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│              ▼                    ▼                │            │
│         Firebase Auth      Sentence Transformer   Gemini API   │
│         - Verify Token     - Create Vectors       - AI Review  │
│                                                                 │
└────────────┬──────────────────────┬───────────────┬────────────┘
             │                      │               │
             ▼                      ▼               ▼
        ┌────────────┐         ┌──────────┐    ┌─────────┐
        │  Firebase  │         │ Pinecone │    │ Gemini  │
        │  Admin SDK │         │ Vectors  │    │   API   │
        │            │         │          │    │         │
        │ - Auth     │         │ - Jobs   │    │ - Review│
        │ - Users    │         │ - Resume │    │- Gen    │
        └────────────┘         └──────────┘    └─────────┘
             │                      │
             └──────────┬───────────┘
                        ▼
            ┌──────────────────────┐
            │  MySQL Database      │
            │  ┌────────────────┐  │
            │  │ users          │  │
            │  │ - firebase_uid │  │
            │  │ - email        │  │
            │  │ - role         │  │
            │  └────────────────┘  │
            │  ┌────────────────┐  │
            │  │ jobs           │  │
            │  │ - admin_id     │  │
            │  │ - title        │  │
            │  │ - vector_id    │  │
            │  └────────────────┘  │
            │  ┌────────────────┐  │
            │  │ applications   │  │
            │  │ - user_id      │  │
            │  │ - job_id       │  │
            │  │ - status       │  │
            │  │ - review       │  │
            │  └────────────────┘  │
            └──────────────────────┘
```

---

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER AUTHENTICATION FLOW               │
└─────────────────────────────────────────────────────────────┘

User Registration:
┌────────────────────────────────────────────────────────────┐
│  1. User fills form: name, email, password, role            │
│     (role: "user" or "admin")                               │
│                                                             │
│  2. Frontend sends to /api/register                          │
│     POST /api/register                                      │
│     {                                                       │
│       "email": "user@example.com",                          │
│       "password": "pass123",                                │
│       "name": "John",                                       │
│       "role": "user"                                        │
│     }                                                       │
│                                                             │
│  3. Backend (app.py):                                       │
│     ✓ Create Firebase user account                          │
│     ✓ Store in MySQL users table with:                      │
│       - firebase_uid (from Firebase)                        │
│       - email                                               │
│       - name                                                │
│       - role                                                │
│     ✓ Respond with user_id                                  │
│                                                             │
│  4. Frontend receives response:                             │
│     ✓ Store in localStorage:                                │
│       - idToken (Firebase token)                            │
│       - user: { user_id, email, name, role }               │
│     ✓ Redirect to /auth page                               │
│                                                             │
└────────────────────────────────────────────────────────────┘

User Login:
┌────────────────────────────────────────────────────────────┐
│  1. User enters email & password                            │
│                                                             │
│  2. Frontend:                                               │
│     ✓ Firebase SDK authenticates: signInWithEmailAndPassword│
│     ✓ Gets idToken from Firebase                            │
│     ✓ Sends idToken to /api/login                           │
│                                                             │
│  3. Backend verifies token:                                 │
│     ✓ auth.verify_id_token(token)                           │
│     ✓ Extract firebase_uid                                  │
│     ✓ Get user from MySQL                                   │
│     ✓ Return user role                                      │
│                                                             │
│  4. Frontend redirects based on role:                       │
│     - role="user" → /user_dashboard                         │
│     - role="admin" → /admin_dashboard                       │
│                                                             │
│  5. Token stored for API calls:                             │
│     Authorization: Bearer <idToken>                         │
│                                                             │
└────────────────────────────────────────────────────────────┘

Protected API Call:
┌────────────────────────────────────────────────────────────┐
│  1. Frontend calls: GET /api/my-applications                │
│     Headers: Authorization: Bearer <idToken>                │
│                                                             │
│  2. Backend @token_required decorator:                      │
│     ✓ Extract token from header                             │
│     ✓ Verify with Firebase: auth.verify_id_token(token)    │
│     ✓ Extract firebase_uid                                  │
│     ✓ Get user from MySQL by firebase_uid                   │
│     ✓ Allow if user exists and token valid                  │
│     ✗ Reject (401) if invalid                               │
│                                                             │
│  3. Backend returns user's applications                     │
│                                                             │
│  4. Frontend handles 401:                                   │
│     - Clear localStorage                                    │
│     - Redirect to /auth                                     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## User Application Flow

```
┌──────────────────────────────────────────────────────────────┐
│             USER APPLIES FOR JOB - COMPLETE FLOW            │
└──────────────────────────────────────────────────────────────┘

1. User views available jobs:
   GET /api/jobs
   ✓ Return list of all jobs from MySQL
   ✓ Display on user_dashboard_new.html

2. User clicks "Apply Now" for a job:
   ✓ Modal opens with job details
   ✓ User selects PDF resume file

3. User submits application:
   POST /api/apply-job
   Content: multipart/form-data
   - job_id: 1
   - resume: <PDF file>
   
4. Backend processes:
   ✓ Extract text from PDF using PyMuPDF (fitz)
   ✓ Generate vector using SentenceTransformer
      - Vector: text embedding (384 dimensions)
   ✓ Upload to Pinecone:
      - ID: uuid4()
      - Vector: [384 floats]
      - Metadata: {type: resume, user_id, job_id, email}
   ✓ Calculate similarity score
   ✓ Store in MySQL applications table:
      - user_id
      - job_id
      - email
      - resume_path
      - pinecone_vector_id
      - score (80.5)
      - status: "pending"

5. Response sent to frontend:
   {
     "message": "Application submitted successfully",
     "score": 80.5,
     "job_title": "Software Engineer"
   }

6. User sees application in "My Applications":
   GET /api/my-applications
   ✓ Shows: job title, score, status, review
   ✓ Status: pending (no review yet)
   ✓ Review: null

7. Admin reviews application (see next flow)

8. User sees updated status:
   ✓ Status: reviewed
   ✓ Review: "Great resume! Here are suggestions..."
   ✓ Can track progress
```

---

## Admin Dashboard Flow (Job-wise)

```
┌──────────────────────────────────────────────────────────────┐
│        ADMIN DASHBOARD - JOB-WISE APPLICANT VIEW            │
└──────────────────────────────────────────────────────────────┘

1. Admin login:
   POST /api/login
   ✓ Verify role = "admin"
   ✓ Redirect to /admin_dashboard

2. Admin sees all their jobs:
   GET /api/admin/all-applicants
   
   Returns for each job:
   {
     "job_id": 1,
     "title": "Senior Engineer",
     "total_applicants": 15,
     "reviewed": 5,
     "accepted": 2,
     "rejected": 1
   }

3. Admin clicks "View Applicants" for specific job:
   ✓ Shows ONLY applicants for that job (JOB-WISE)
   ✓ No mixing with other jobs!

4. Backend GET /api/admin/job-applicants/<job_id>?top_k=20
   ✓ Query: SELECT * FROM applications 
            WHERE job_id = ? 
            ORDER BY score DESC 
            LIMIT 20
   ✓ Join with jobs table for titles
   ✓ Return top K sorted by score (highest first)

5. For each applicant, admin can:
   
   a) Generate AI Review:
      POST /api/admin/generate-review/<app_id>
      ✓ Extract resume PDF
      ✓ Send to Gemini API with prompt
      ✓ Get generated review
      ✓ Save in applications.review
      ✓ Update status to "reviewed"
   
   b) Manual Review:
      POST /api/admin/review-application/<app_id>
      {
        "status": "accepted",
        "review": "Great match for our team!"
      }
      ✓ Save in applications.review
      ✓ Update applications.status
      ✓ Set applications.reviewed_by = admin_id
      ✓ Set applications.reviewed_at = NOW()
   
   c) Quick Actions:
      - Accept ✅ (status=accepted)
      - Reject ❌ (status=rejected)
      - View Resume 📄

6. Statistics updated in real-time:
   ✓ Total applicants: 15
   ✓ Reviewed: 5 → 6
   ✓ Accepted: 2
   ✓ Rejected: 1

7. User management per job:
   ✓ Each job shows applicants ONLY for that job
   ✓ No mixing across multiple jobs
   ✓ Clear separation and filtering
```

---

## Data Flow - Vector Storage

```
┌──────────────────────────────────────────────────────────────┐
│          VECTOR STORAGE IN PINECONE                          │
└──────────────────────────────────────────────────────────────┘

When Admin Posts Job:
────────────────────
1. Title + Description → Sentence Transformer
   "Senior Software Engineer - 5+ years experience"
   ↓
   Vector: [0.234, -0.123, 0.456, ..., 0.111] (384 dims)

2. Store in Pinecone:
   upsert(vectors=[
     {
       "id": "job-uuid-123",
       "values": [0.234, -0.123, ..., 0.111],
       "metadata": {
         "type": "job",
         "title": "Senior Software Engineer",
         "job_id": 1
       }
     }
   ])

3. Also store in MySQL:
   INSERT INTO jobs (title, description, pinecone_vector_id)
   VALUES (..., "job-uuid-123")


When User Applies:
──────────────────
1. Resume PDF → Extract Text
   "Worked at Google for 5 years..."
   ↓
   Vector: [0.222, -0.111, 0.445, ..., 0.100] (384 dims)

2. Store in Pinecone:
   upsert(vectors=[
     {
       "id": "resume-uuid-456",
       "values": [0.222, -0.111, ..., 0.100],
       "metadata": {
         "type": "resume",
         "user_id": 5,
         "job_id": 1,
         "email": "user@example.com"
       }
     }
   ])

3. Calculate Similarity:
   Cosine similarity between vectors
   = 0.85 (scale 0-1)
   = 85% match
   
4. Store in MySQL:
   INSERT INTO applications 
   (user_id, job_id, pinecone_vector_id, score)
   VALUES (5, 1, "resume-uuid-456", 85.0)


Benefits over MySQL:
────────────────────
✅ Faster similarity searches (Pinecone optimized)
✅ Better semantic matching (specialized algorithms)
✅ Scalable to millions of vectors
✅ No JSON parsing overhead
✅ Metadata filtering built-in
```

---

## Database Schema Relationships

```
users
├── id (PK)
├── firebase_uid (UNIQUE)
├── email (UNIQUE)
├── name
├── role (user / admin)
└── resume_path

    ▼
    
jobs (admin posts these)
├── id (PK)
├── admin_id (FK → users.id)
├── title
├── description
├── pinecone_vector_id
└── created_at

    ▼
    
applications (user → job bridge)
├── id (PK)
├── user_id (FK → users.id)
├── job_id (FK → jobs.id)
├── email
├── name
├── resume_path
├── pinecone_vector_id
├── score
├── status (pending/reviewed/accepted/rejected)
├── review (AI/admin feedback)
├── reviewed_by (FK → users.id, nullable)
├── reviewed_at (TIMESTAMP, nullable)
└── submitted_at

Key Relationships:
- One user can have many jobs (if admin)
- One user can have many applications (if job seeker)
- One job can have many applications
- One admin review can affect multiple users (reviewed_by)
```

---

## API Call Sequence - Complete User Journey

```
┌──────────────────────────────────────────────────────────────┐
│              COMPLETE USER JOURNEY SEQUENCE                  │
└──────────────────────────────────────────────────────────────┘

1️⃣  REGISTRATION (User)
    POST /api/register
    ✓ Create Firebase account
    ✓ Store in MySQL users table
    ✓ Return user_id, role="user"
    ✓ Frontend stores idToken

2️⃣  LOGIN (User)
    POST /api/login
    ✓ Firebase token verified
    ✓ MySQL lookup by firebase_uid
    ✓ Redirect to /user_dashboard

3️⃣  VIEW JOBS (User)
    GET /api/jobs
    ✓ Return all jobs from jobs table
    ✓ Display in UI

4️⃣  APPLY FOR JOB (User)
    POST /api/apply-job
    ✓ Resume PDF uploaded
    ✓ Text extracted
    ✓ Vector generated
    ✓ Uploaded to Pinecone
    ✓ Stored in MySQL applications table
    ✓ Score calculated

5️⃣  VIEW MY APPLICATIONS (User)
    GET /api/my-applications
    ✓ Query applications WHERE user_id = current_user
    ✓ Join with jobs for titles
    ✓ Return with status, review, scores
    ✓ Show pending status (no review yet)

6️⃣  REGISTRATION (Admin)
    POST /api/register (role="admin")
    ✓ Same as user but role="admin"

7️⃣  LOGIN (Admin)
    POST /api/login
    ✓ Verify role="admin"
    ✓ Redirect to /admin_dashboard

8️⃣  POST JOB (Admin)
    POST /api/admin/jobs
    ✓ Job description vectorized
    ✓ Vector uploaded to Pinecone
    ✓ Stored in MySQL jobs table with admin_id

9️⃣  VIEW JOBS WITH STATS (Admin)
    GET /api/admin/all-applicants
    ✓ Show admin's jobs (WHERE admin_id = current_admin)
    ✓ Return with total, reviewed, accepted, rejected counts

🔟 VIEW APPLICANTS FOR SPECIFIC JOB (Admin)
    GET /api/admin/job-applicants/<job_id>?top_k=20
    ✓ Query applications WHERE job_id = <job_id> (JOB-WISE!)
    ✓ Sort by score DESC
    ✓ Return top 20

1️⃣1️⃣  GENERATE AI REVIEW (Admin)
    POST /api/admin/generate-review/<app_id>
    ✓ Extract resume from applications table
    ✓ Send to Gemini API
    ✓ Get generated review
    ✓ Save in applications.review
    ✓ Update status to "reviewed"

1️⃣2️⃣  MANUAL REVIEW (Admin)
    POST /api/admin/review-application/<app_id>
    ✓ Save status (accepted/rejected/reviewed)
    ✓ Save review text
    ✓ Set reviewed_by = admin_id
    ✓ Set reviewed_at = NOW()

1️⃣3️⃣  USER SEES REVIEW
    GET /api/my-applications
    ✓ Check applications status
    ✓ See status = "reviewed"
    ✓ Display review from admin
    ✓ See if accepted/rejected
```

---

## Key Improvements Over Old System

```
OLD SYSTEM:
──────────
- No authentication
  → Anyone could access admin/user pages
  
- Vectors in MySQL (JSON strings)
  → Slow similarity searching
  → Not scalable
  
- All applicants mixed
  → Hard to filter by job
  → Confusing interface
  
- No application tracking
  → User doesn't know application status
  → No feedback loop
  
- Manual reviews only
  → Tedious for admins
  → No AI assistance


NEW SYSTEM:
───────────
✅ Firebase Authentication
   → Separate user/admin roles
   → Secure login/register
   
✅ Pinecone Vector Storage
   → Fast semantic search
   → Scalable to millions
   → Built-in similarity
   
✅ Job-wise Filtering
   → Admin sees applicants per job
   → Clear organization
   → Easy navigation
   
✅ Application Dashboard
   → Users track applications
   → See scores & status
   → Get feedback
   
✅ AI Reviews
   → Auto-generate with Gemini
   → Save admin time
   → Plus manual review option
```

Great! Now you have complete understanding of how everything works together! 🚀
