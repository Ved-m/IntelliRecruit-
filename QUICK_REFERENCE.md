# ⚡ QUICK REFERENCE CARD

## 📋 WHAT'S NEW - FEATURE SUMMARY

| Feature | Old System | New System |
|---------|-----------|-----------|
| **Authentication** | ❌ None | ✅ Firebase (user/admin roles) |
| **Vector Storage** | MySQL JSON | ✅ Pinecone (fast, scalable) |
| **Admin View** | All applicants mixed | ✅ Job-wise filtering |
| **User Dashboard** | ❌ Not available | ✅ Track applications + reviews |
| **AI Reviews** | ❌ Manual only | ✅ AI + Manual hybrid |
| **Security** | Minimal | ✅ Token-based + Role-based |

---

## 🚀 TIMELINE

| Step | Time | Checklist |
|------|------|-----------|
| 1. Firebase Setup | 10 min | [ ] Create project, Enable auth, Download key |
| 2. Package Installation | 5 min | [ ] `pip install -r requirements.txt` |
| 3. Configuration | 5 min | [ ] Create & fill .env file |
| 4. Update HTML | 5 min | [ ] Update Firebase config in 3 HTML files |
| 5. Database Setup | 5 min | [ ] Run `mysql < database.sql` & verify |
| 6. Pinecone Setup | 10 min | [ ] Create account, index, add API key |
| 7. Verification | 5 min | [ ] Run `python verify_setup.py` |
| 8. Backup & Deploy | 5 min | [ ] Backup old app, copy new app.py |
| **TOTAL** | **~55 min** | **Ready to test!** |

---

## 📁 FILE LOCATIONS

```
d:\vit\4 sem\job_recommendation_system\
├── app.py                          ← Replace with app_new.py
├── app_new.py                      ← NEW (main backend)
├── app_old.py                      ← Backup of old app
│
├── firebase-key.json               ← Download from Firebase Console
├── .env                            ← Configure with your keys
├── requirements.txt                ← Updated, run pip install
├── database.sql                    ← Run in MySQL
│
├── verify_setup.py                 ← Run to check everything
│
├── SETUP_SUMMARY.md               ← Start here
├── FIREBASE_SETUP_GUIDE.md        ← Step-by-step instructions
├── IMPLEMENTATION_GUIDE.md        ← Complete API docs
├── ARCHITECTURE_DIAGRAMS.md       ← System design
│
└── templates/
    ├── auth.html                  ← NEW (login/register)
    ├── user_dashboard_new.html    ← NEW (user dashboard)
    ├── admin_dashboard_new.html   ← NEW (admin dashboard)
    ├── user_dashboard_old.html    ← Backup
    └── admin_dashboard_old.html   ← Backup
```

---

## 🔐 KEY CREDENTIALS TO GET

### From Firebase Console:
```
☐ FIREBASE_API_KEY
☐ FIREBASE_PROJECT_ID
☐ FIREBASE_AUTH_DOMAIN
☐ FIREBASE_DATABASE_URL
☐ Firebase Service Account Key (firebase-key.json)
```

### From Pinecone:
```
☐ PINECONE_API_KEY
☐ PINECONE_INDEX_NAME (create index first)
```

### From Google Gemini:
```
☐ GENAI_API_KEY (for AI reviews)
```

### MySQL:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=123456
DB_NAME=job_db
```

---

## 🧪 QUICK TEST COMMANDS

```bash
# Verify environment
python verify_setup.py

# Check Python version
python --version

# Check packages
pip list | grep -E "flask|firebase|pinecone"

# Test database connection
mysql -u root -p123456 job_db -e "SELECT COUNT(*) FROM users;"

# Run app
python app.py

# Check if running
curl http://localhost:5000/auth
```

---

## 🐛 COMMON ERRORS & FIXES

### "firebase-key.json not found"
```
Fix: Download from Firebase Console > Settings > Service Accounts
     Place in: d:\vit\4 sem\job_recommendation_system\firebase-key.json
```

### "ModuleNotFoundError: No module named 'firebase_admin'"
```
Fix: pip install -r requirements.txt
```

### "Database connection failed"
```
Fix: 
1. Ensure MySQL running: mysql -V
2. Check credentials in .env
3. Run: mysql -u root -p123456 < database.sql
```

### "Pinecone connection failed"
```
Fix:
1. Check PINECONE_API_KEY in .env
2. Create index in Pinecone dashboard
3. Dimension = 384
4. Metric = cosine
```

### "Token verification failed"
```
Fix:
1. Check firebase-key.json is valid JSON
2. Verify FIREBASE_PROJECT_ID matches
3. Clear browser localStorage
4. Re-login
```

### "Admin can't see applicants"
```
Fix:
1. Ensure role='admin' in database
2. Ensure job admin_id matches current admin
3. Clear cache and full browser refresh
```

---

## 📤 DEPLOYMENT CHECKLIST

- [ ] Run `python verify_setup.py` - all green ✅
- [ ] Test registration (user account)
- [ ] Test login as user
- [ ] Test registration (admin account)
- [ ] Test login as admin
- [ ] Admin post a job ✅
- [ ] User applies for job ✅
- [ ] Admin views job applicants ✅ (not all!)
- [ ] Admin generates AI review ✅
- [ ] User sees review in dashboard ✅
- [ ] Admin can accept/reject ✅
- [ ] User sees status update ✅
- [ ] Logout/Login cycles work
- [ ] Token refresh works
- [ ] Error messages display properly

---

## 🎯 ENDPOINTS QUICK REFERENCE

### Public (No Auth Required)
```
POST   /api/register
POST   /api/login
GET    /api/jobs
```

### User Protected
```
GET    /api/user-profile
POST   /api/apply-job
GET    /api/my-applications
```

### Admin Protected
```
POST   /api/admin/jobs
DELETE /api/jobs/<id>
GET    /api/admin/all-applicants
GET    /api/admin/job-applicants/<job_id>
POST   /api/admin/review-application/<id>
POST   /api/admin/generate-review/<id>
```

---

## 📞 SUPPORT FILES

| Document | Purpose |
|----------|---------|
| SETUP_SUMMARY.md | Overview + checklist |
| FIREBASE_SETUP_GUIDE.md | Step-by-step Firebase setup |
| IMPLEMENTATION_GUIDE.md | Complete API documentation |
| ARCHITECTURE_DIAGRAMS.md | System design & flows |
| verify_setup.py | Automated verification |

---

## ✨ AFTER SUCCESSFUL DEPLOYMENT

### User Features:
```
✅ Register with email/password
✅ Login securely
✅ Browse available jobs
✅ Apply for jobs with resume
✅ View application status
✅ See admin reviews & feedback
✅ Track multiple applications
```

### Admin Features:
```
✅ Register as recruiter
✅ Post new jobs
✅ View jobs with statistics
✅ See TOP K applicants PER JOB (job-wise!)
✅ Generate AI reviews instantly
✅ Write manual reviews
✅ Accept/reject applicants
✅ Track review progress
```

### System Features:
```
✅ Secure authentication (Firebase)
✅ Fast vector search (Pinecone)
✅ AI-powered reviews (Gemini)
✅ Role-based access control
✅ Real-time status updates
✅ Scalable architecture
```

---

## 🚨 IMPORTANT REMINDERS

1. **Don't commit firebasekey.json** to git (add to .gitignore)
2. **Update Firebase config** in all 3 HTML files (not generated automatically)
3. **Backup old files** before replacing app.py
4. **Run verify_setup.py** before starting app
5. **MySQL must be running** before launching Flask
6. **Pinecone free tier** has limits (check limits if many uploads)

---

## 💡 PRO TIPS

- Use `python verify_setup.py` to diagnose issues
- Check Flask logs in terminal for backend errors
- Check browser console (F12) for frontend errors
- Test with curl for API debugging:
  ```bash
  curl -H "Authorization: Bearer <token>" \
       http://localhost:5000/api/my-applications
  ```
- Keep separate test accounts for user/admin
- Test on localhost first before production deployment

---

## 🎓 LEARNING RESOURCES

- Firebase Docs: https://firebase.google.com/docs
- Pinecone Docs: https://docs.pinecone.io/
- Sentence Transformers: https://www.sbert.net/
- Flask Documentation: https://flask.palletsprojects.com/

---

**You're all set! Start with FIREBASE_SETUP_GUIDE.md → Follow steps → Test → Done! 🚀**
