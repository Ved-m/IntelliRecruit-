import os
import pymysql
import json
import fitz
import numpy as np
import uuid
import firebase_admin
from firebase_admin import credentials, auth, db
from functools import wraps
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "="*60)
print("🟢 JOB RECOMMENDATION SYSTEM STARTING")
print("="*60)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# ==================== FIREBASE INITIALIZATION ====================
try:
    print("\n" + "="*60)
    print("🔵 INITIALIZING APPLICATION")
    print("="*60)
    
    cred = credentials.Certificate('firebase-key.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
    })
    print("✓ Firebase initialized successfully")
except Exception as e:
    print(f"⚠ Firebase initialization warning: {e}")

# ==================== PINECONE INITIALIZATION ====================
try:
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index(os.getenv('PINECONE_INDEX_NAME'))
    print("✓ Pinecone initialized successfully")
except Exception as e:
    print(f"⚠ Pinecone initialization warning: {e}")
    index = None

# ==================== DATABASE CONFIGURATION ====================
def get_db_connection():
    try:
        host = os.getenv('DB_HOST', 'localhost')
        user = os.getenv('DB_USER', 'root')
        database = os.getenv('DB_NAME', 'job_db')
        
        conn = pymysql.connect(
            host=host,
            user=user,
            password=os.getenv('DB_PASSWORD', '123456'),
            database=database,
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✓ MySQL Connection OK - {user}@{host}/{database}")
        return conn
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        print(f"Attempted: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_USER', 'root')}@{os.getenv('DB_NAME', 'job_db')}")
        return None

# Load Sentence Transformer Model - LAZY LOAD (on first use)
model = None

def get_model():
    """Load model on first use"""
    global model
    if model is None:
        print("🔵 Loading Sentence Transformer model... (first time only)")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded successfully")
    return model

# Configure Gemini API
genai.configure(api_key=os.getenv('GENAI_API_KEY'))

# Ensure uploads folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ==================== AUTHENTICATION DECORATORS ====================
def token_required(f):
    """Verify Firebase token and get user info"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            # Verify Firebase token
            decoded_token = auth.verify_id_token(token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email')
            
            # Get user from database
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, role, email FROM users WHERE firebase_uid = %s", (firebase_uid,))
                user = cursor.fetchone()
            conn.close()
            
            if not user:
                return jsonify({"error": "User not found in database"}), 401
            
            # Add user info to kwargs
            kwargs['current_user'] = {
                'firebase_uid': firebase_uid,
                'user_id': user['id'],
                'email': user['email'],
                'role': user['role']
            }
            
            return f(*args, **kwargs)
        
        except Exception as e:
            print(f"Token verification error: {e}")
            return jsonify({"error": "Invalid token"}), 401
    
    return decorated_function

def admin_required(f):
    """Verify user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            decoded_token = auth.verify_id_token(token)
            firebase_uid = decoded_token['uid']
            
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, role FROM users WHERE firebase_uid = %s", (firebase_uid,))
                user = cursor.fetchone()
            conn.close()
            
            if not user or user['role'] != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            kwargs['current_user'] = {
                'user_id': user['id'],
                'role': user['role']
            }
            
            return f(*args, **kwargs)
        
        except Exception as e:
            print(f"Token verification error: {e}")
            return jsonify({"error": "Invalid token"}), 401
    
    return decorated_function

# ==================== FIREBASE AUTH ROUTES ====================
@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user - Firebase user already created by frontend"""
    try:
        print("\n" + "="*50)
        print("🔵 REGISTER REQUEST RECEIVED")
        print("="*50)
        
        data = request.get_json()
        print(f"Request data keys: {data.keys() if data else None}")
        
        email = data.get('email')
        name = data.get('name')
        role = data.get('role', 'user')  # 'user' or 'admin'
        firebase_uid = data.get('firebase_uid')  # ← Sent from frontend
        
        print(f"Email: {email}")
        print(f"Name: {name}")
        print(f"Role: {role}")
        print(f"Firebase UID: {firebase_uid}")
        
        if not email or not name or not firebase_uid:
            print("❌ Missing required fields")
            return jsonify({"error": "Email, name, and firebase_uid are required"}), 400
        
        if role not in ['user', 'admin']:
            print("❌ Invalid role")
            return jsonify({"error": "Role must be 'user' or 'admin'"}), 400
        
        # Store in MySQL (user already created in Firebase by frontend)
        print(f"✓ Storing in MySQL...")
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return jsonify({"error": "Database connection failed"}), 500
            
        try:
            with conn.cursor() as cursor:
                sql = "INSERT INTO users (firebase_uid, email, name, role) VALUES (%s, %s, %s, %s)"
                print(f"Executing SQL: {sql}")
                cursor.execute(sql, (firebase_uid, email, name, role))
            conn.commit()
            
            # Get the inserted user_id
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE firebase_uid = %s", (firebase_uid,))
                user = cursor.fetchone()
                user_id = user['id'] if user else None
            
            conn.close()
            print(f"✓ User stored in MySQL! user_id: {user_id}")
            
            print("✅ REGISTRATION SUCCESSFUL\n")
            
            return jsonify({
                "message": "User registered successfully",
                "user_id": user_id,
                "firebase_uid": firebase_uid,
                "email": email,
                "name": name,
                "role": role
            }), 201
        except Exception as db_error:
            conn.close()
            if "Duplicate entry" in str(db_error):
                print("❌ Email already exists")
                return jsonify({"error": "Email already registered"}), 400
            raise
    
    except firebase_admin.auth.EmailAlreadyExistsError:
        print("❌ Email already exists in Firebase")
        return jsonify({"error": "Email already exists"}), 400
    except firebase_admin.auth.InvalidEmailError:
        print("❌ Invalid email format")
        return jsonify({"error": "Invalid email format"}), 400
    except Exception as e:
        print(f"\n❌ REGISTRATION ERROR: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}\n")
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint - receives Firebase ID token from frontend"""
    try:
        print("\n" + "="*50)
        print("🔵 LOGIN REQUEST RECEIVED")
        print("="*50)
        
        data = request.get_json()
        print(f"Request data keys: {data.keys() if data else None}")
        
        id_token = data.get('idToken')
        print(f"ID token received: {bool(id_token)}")
        print(f"Token length: {len(id_token) if id_token else 0}")
        
        if not id_token:
            print("❌ No ID token provided")
            return jsonify({"error": "ID token is required"}), 400
        
        # Verify token
        print(f"✓ Verifying Firebase token...")
        decoded_token = auth.verify_id_token(id_token)
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        print(f"✓ Token verified! UID: {firebase_uid}, Email: {email}")
        
        # Get user from database
        print(f"✓ Fetching user from MySQL...")
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, role, name FROM users WHERE firebase_uid = %s", (firebase_uid,))
            user = cursor.fetchone()
        conn.close()
        
        if not user:
            print(f"❌ User not found in MySQL for firebase_uid: {firebase_uid}")
            return jsonify({"error": "User not found"}), 404
        
        print(f"✓ User found! ID: {user['id']}, Name: {user['name']}, Role: {user['role']}")
        print("✅ LOGIN SUCCESSFUL\n")
        
        return jsonify({
            "message": "Login successful",
            "user_id": user['id'],
            "email": email,
            "name": user['name'],
            "role": user['role'],
            "idToken": id_token
        }), 200
    
    except Exception as e:
        print(f"\n❌ LOGIN ERROR: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}\n")
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/user-profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    """Get current user profile"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, name, role, resume_path, created_at 
                FROM users WHERE id = %s
            """, (current_user['user_id'],))
            user = cursor.fetchone()
        conn.close()
        
        return jsonify(user), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== JOB ROUTES ====================
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, description FROM jobs")
            jobs = cursor.fetchall()
        conn.close()
        return jsonify(jobs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/jobs', methods=['POST'])
@admin_required
def upload_job(current_user):
    """Upload a new job (admin only)"""
    try:
        print("\n" + "="*50)
        print("🔵 UPLOADING NEW JOB")
        print("="*50)
        
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        
        print(f"Title: {title}")
        print(f"Description length: {len(description) if description else 0}")
        
        if not title or not description:
            print("❌ Missing title or description")
            return jsonify({"error": "Title and description required"}), 400
        
        # Store in MySQL FIRST to get the job_id
        print("💾 Storing job in MySQL...")
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO jobs (admin_id, title, description, pinecone_vector_id) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (current_user['user_id'], title, description, 'temp'))
        conn.commit()
        
        # Get the inserted job_id
        with conn.cursor() as cursor:
            cursor.execute("SELECT LAST_INSERT_ID() as job_id")
            result = cursor.fetchone()
            job_id = result['job_id']
        
        print(f"✅ Job stored in MySQL with ID: {job_id}")
        
        # Create vector for job
        print("📊 Creating job vector...")
        job_vector = get_model().encode(description).tolist()
        print(f"✅ Vector created (dimension: {len(job_vector)})")
        
        # Store in Pinecone WITH job_id in metadata
        job_vector_id = str(uuid.uuid4())
        if index:
            print(f"📤 Uploading job vector to Pinecone...")
            index.upsert(vectors=[(
                job_vector_id,
                job_vector,
                {
                    "type": "job",
                    "job_id": job_id,  # ← NOW INCLUDES job_id
                    "title": title,
                    "description": description
                }
            )])
            print(f"✅ Job vector uploaded: {job_vector_id}")
            
            # Update MySQL with the actual vector ID
            with conn.cursor() as cursor:
                cursor.execute("UPDATE jobs SET pinecone_vector_id = %s WHERE id = %s", (job_vector_id, job_id))
            conn.commit()
            print(f"✅ MySQL updated with vector ID")
        
        conn.close()
        
        print("✅ JOB UPLOAD SUCCESSFUL\n")
        
        return jsonify({
            "message": "Job uploaded successfully",
            "job_id": job_id,
            "job_vector_id": job_vector_id
        }), 201
    except Exception as e:
        print(f"❌ Job upload error: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@admin_required
def delete_job(job_id, current_user):
    """Delete a job (admin only)"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if job exists and belongs to admin
            cursor.execute("SELECT pinecone_vector_id FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({"error": "Job not found"}), 404
            
            # Delete from Pinecone
            if index and job['pinecone_vector_id']:
                try:
                    index.delete(ids=[job['pinecone_vector_id']])
                except:
                    pass
            
            # Delete related applications first
            cursor.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
            
            # Delete job
            cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Job deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== APPLICATION ROUTES ====================
def extract_text_from_pdf(pdf_path):
    """Extract text from PDF"""
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text.strip() if text else None
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

@app.route('/api/apply-job', methods=['POST'])
@token_required
def apply_job(current_user):
    """Apply for a job"""
    try:
        job_id = request.form.get('job_id')
        resume_file = request.files.get('resume')
        
        if not job_id or not resume_file:
            return jsonify({"error": "Job ID and resume required"}), 400
        
        if not resume_file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files allowed"}), 400
        
        # Save resume
        unique_filename = f"{uuid.uuid4()}.pdf"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        resume_file.save(file_path)
        
        # Extract text and create vector
        resume_text = extract_text_from_pdf(file_path)
        if not resume_text:
            return jsonify({"error": "Failed to extract resume text"}), 400
        
        resume_vector = get_model().encode(resume_text).tolist()
        
        # Get job info and calculate score
        conn = get_db_connection()
        score = 0.0
        job = None
        job_vector_id = None
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, pinecone_vector_id FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({"error": "Job not found"}), 404
            
            job_vector_id = job.get('pinecone_vector_id')
        
        # Calculate similarity score using Pinecone
        if index and job_vector_id:
            try:
                print(f"📊 Calculating similarity score for resume vs job {job_id}")
                # Query Pinecone to find similarity between resume and job vectors
                results = index.query(
                    vector=resume_vector,
                    top_k=1,
                    filter={"type": "job", "job_id": int(job_id)}
                )
                if results['matches'] and len(results['matches']) > 0:
                    # Score from Pinecone is 0-1, convert to 0-100
                    score = round(results['matches'][0]['score'] * 100, 2)
                    print(f"✅ Similarity score calculated: {score}%")
                else:
                    print(f"⚠️  No matching job vector found in Pinecone")
                    score = 0.0
            except Exception as e:
                print(f"⚠️  Error calculating score: {e}")
                score = 0.0
        
        # Store resume vector in Pinecone
        vector_id = str(uuid.uuid4())
        if index:
            print(f"📤 Uploading resume vector to Pinecone...")
            try:
                index.upsert(vectors=[(
                    vector_id,
                    resume_vector,
                    {
                        "type": "resume",
                        "user_id": current_user['user_id'],
                        "job_id": int(job_id),
                        "email": current_user['email']
                    }
                )])
                print(f"✅ Resume vector uploaded to Pinecone: {vector_id}")
            except Exception as e:
                print(f"❌ Error uploading to Pinecone: {e}")

        
        # Store in MySQL
        print(f"💾 Storing application in MySQL...")
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO applications 
                (user_id, job_id, email, name, resume, pinecone_vector_id, score, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            """
            print(f"SQL: {sql}")
            print(f"Values: user_id={current_user['user_id']}, job_id={job_id}, score={score}, vector_id={vector_id}")
            cursor.execute(sql, (
                current_user['user_id'],
                job_id,
                current_user['email'],
                current_user.get('name', ''),
                file_path,
                vector_id,
                score
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Application submitted with score: {score}%")
        
        return jsonify({
            "message": "Application submitted successfully",
            "score": score,
            "job_title": job['title'],
            "vector_id": vector_id
        }), 201
    
    except Exception as e:
        print(f"Application error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/my-applications', methods=['GET'])
@token_required
def get_my_applications(current_user):
    """Get user's applications with status and reviews"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT a.id, j.title, a.score, a.status, a.review, 
                       a.submitted_at, a.reviewed_at, u.name as reviewed_by
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                LEFT JOIN users u ON a.reviewed_by = u.id
                WHERE a.user_id = %s
                ORDER BY a.submitted_at DESC
            """
            cursor.execute(sql, (current_user['user_id'],))
            applications = cursor.fetchall()
        conn.close()
        
        return jsonify(applications), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== ADMIN DASHBOARD ROUTES ====================
@app.route('/api/admin/job-applicants/<int:job_id>', methods=['GET'])
@admin_required
def get_job_applicants(job_id, current_user):
    """Get top K applicants for a specific job"""
    try:
        top_k = request.args.get('top_k', 10, type=int)
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Verify job belongs to admin
            cursor.execute("SELECT id FROM jobs WHERE id = %s AND admin_id = %s", 
                         (job_id, current_user['user_id']))
            if not cursor.fetchone():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Get top K applicants for this job
            sql = """
                SELECT a.id, a.name, a.email, a.score, a.status, a.review, 
                       a.submitted_at, a.reviewed_at, j.title
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.job_id = %s
                ORDER BY a.score DESC
                LIMIT %s
            """
            cursor.execute(sql, (job_id, top_k))
            applicants = cursor.fetchall()
        conn.close()
        
        return jsonify(applicants), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/all-applicants', methods=['GET'])
@admin_required
def get_all_applicants(current_user):
    """Get all applicants grouped by job"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id as job_id, j.title, 
                       COUNT(a.id) as total_applicants,
                       COUNT(CASE WHEN a.status = 'reviewed' THEN 1 END) as reviewed,
                       COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) as accepted,
                       COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected
                FROM jobs j
                LEFT JOIN applications a ON j.id = a.job_id
                WHERE j.admin_id = %s
                GROUP BY j.id, j.title
                ORDER BY j.created_at DESC
            """
            cursor.execute(sql, (current_user['user_id'],))
            job_stats = cursor.fetchall()
        conn.close()
        
        return jsonify(job_stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/review-application/<int:app_id>', methods=['POST'])
@admin_required
def review_application(app_id, current_user):
    """Submit review and status for an application"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'accepted', 'rejected', 'pending'
        review = data.get('review')
        
        if status not in ['accepted', 'rejected', 'reviewed', 'pending']:
            return jsonify({"error": "Invalid status"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Verify application belongs to admin's job
            cursor.execute("""
                SELECT a.id FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.admin_id = %s
            """, (app_id, current_user['user_id']))
            
            if not cursor.fetchone():
                return jsonify({"error": "Unauthorized"}), 403
            
            # Update application
            sql = """
                UPDATE applications 
                SET status = %s, review = %s, reviewed_by = %s, reviewed_at = NOW()
                WHERE id = %s
            """
            cursor.execute(sql, (status, review, current_user['user_id'], app_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Application reviewed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_review(resume_text):
    """Generate AI review of resume"""
    try:
        prompt = f"""
        You are an AI career coach. Analyze this resume and provide improvement suggestions:
        - Clarity and conciseness
        - Relevant skills and experience  
        - Formatting and structure
        - Action verbs and quantifiable achievements
        - Grammar and spelling
        
        Resume: {resume_text}
        
        Provide constructive suggestions:
        """
        
        model_instance = genai.GenerativeModel("gemini-1.5-pro")
        response = model_instance.generate_content(prompt)
        return response.text if response.text else "Could not generate review"
    except Exception as e:
        print(f"Review generation error: {e}")
        return "Error generating review"

@app.route('/api/admin/generate-review/<int:app_id>', methods=['POST'])
@admin_required
def generate_review_endpoint(app_id, current_user):
    """Generate AI review for an application"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get application
            cursor.execute("""
                SELECT a.resume, a.id FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.admin_id = %s
            """, (app_id, current_user['user_id']))
            
            app = cursor.fetchone()
            if not app:
                return jsonify({"error": "Unauthorized"}), 403
            
            # Extract and generate review
            resume_text = extract_text_from_pdf(app['resume'])
            if not resume_text:
                return jsonify({"error": "Failed to extract resume"}), 400
            
            review = generate_review(resume_text)
            
            # Save review
            cursor.execute("""
                UPDATE applications 
                SET review = %s, status = 'reviewed'
                WHERE id = %s
            """, (review, app_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"review": review}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== NEW ROUTES ====================
@app.route('/auth')
def auth_page():
    print("🔵 GET /auth - Auth page requested")
    return render_template('auth.html')

@app.route('/user_dashboard')
def user_dashboard():
    print("🔵 GET /user_dashboard - User dashboard requested")
    return render_template('user_dashboard_new.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    print("🔵 GET /admin_dashboard - Admin dashboard requested")
    return render_template('admin_dashboard_new.html')

# ==================== LEGACY ROUTES (will be deprecated) ====================
@app.route('/')
def home():
    return render_template('auth.html')

@app.route('/admin')
def admin():
    return render_template('admin_upload_job.html')

@app.route('/admin_panel')
def admin_panel():
    return render_template('admin_panel.html')

@app.route('/manage_jobs')
def manage_jobs():
    return render_template('manage_jobs.html')

# ==================== RUN APP ====================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🟢 FLASK APP STARTING ON http://127.0.0.1:5000")
    print("="*60)
    print("✓ Go to http://127.0.0.1:5000/auth to register/login")
    print("✓ All logs below will show detailed request/response info")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
