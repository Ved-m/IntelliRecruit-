import os
import pymysql
import json
import fitz  # PyMuPDF for extracting text from PDFs
import numpy as np
import uuid
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline  # Hugging Face model
import ollama
import google.generativeai as genai

app = Flask(__name__)

# Database Configuration
def get_db_connection():
    try:
        conn = pymysql.connect(
            host="localhost", user="root", password="123456", database="job_db", cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print("Database Connection Error:", e)
        return None

# Load Sentence Transformer Model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load Hugging Face model for review generation
# review_generator = pipeline("text-generation", model="gpt2")


import requests

# Configure Gemini API
GENAI_API_KEY = ""
genai.configure(api_key=GENAI_API_KEY)


def generate_review(resume_text):
    prompt = f"""
    You are an AI career coach. Analyze the following resume and provide improvement suggestions:
    
    - Clarity and conciseness
    - Relevance of skills and experience to the job
    - Formatting and structure
    - Use of action verbs and quantifiable achievements
    - Grammar and spelling

    Resume:
    {resume_text}

    Suggestions:
    """

    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)

    return response.text if response.text else "Could not generate review."
    

# Ensure uploads folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ------------------ ROUTES ------------------
@app.route("/")
def home():
    return render_template("user_dashboard.html")

@app.route("/admin")
def admin():
    return render_template("admin_upload_job.html")

@app.route('/admin_panel')
def admin_panel():
    return render_template('admin_panel.html')
#-----------------------------------------------------------
@app.route('/search_results')
def search_results():
    """Render the search results page"""
    return render_template('search_results.html')

@app.route("/upload_job", methods=["POST"])
def upload_job():
    try:
        data = request.get_json()
        title = data.get("title")
        description = data.get("description")

        if not title or not description:
            return jsonify({"error": "Title and description are required!"}), 400

        job_vector = model.encode(description).tolist()
        job_vector_str = json.dumps(job_vector)

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed!"}), 500

        with conn.cursor() as cursor:
            sql = "INSERT INTO jobs (title, description, vector) VALUES (%s, %s, %s)"
            cursor.execute(sql, (title, description, job_vector_str))
        conn.commit()
        return jsonify({"message": "Job uploaded successfully!"})

    except Exception as e:
        print("Error uploading job:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/get_jobs", methods=["GET"])
def get_jobs():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, description FROM jobs")
            jobs = cursor.fetchall()
        return jsonify(jobs)
    finally:
        conn.close()

def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text.strip() if text else None
    except Exception as e:
        print("Error extracting text from PDF:", e)
        return None
    
@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    name = request.form.get("name")
    email = request.form.get("email")
    job_id = request.form.get("job_id")
    resume_file = request.files.get("resume")
    
    if not name or not email or not resume_file or not job_id:
        return jsonify({"error": "All fields are required"}), 400
    
    if not resume_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    unique_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    resume_file.save(file_path)
    
    text = extract_text_from_pdf(file_path)
    if text is None:
        return jsonify({"error": "Failed to extract text from resume. Please upload a valid PDF."}), 400
    
    resume_vector = model.encode(text).tolist()
    resume_vector_str = json.dumps(resume_vector)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT vector FROM jobs WHERE id = %s", (job_id,))
            job_vectors = cursor.fetchall()
            
            if not job_vectors:
                return jsonify({"error": "Job not found or no vectors available"}), 404
            
            similarity_scores = []
            for job in job_vectors:
                job_vector = np.array(json.loads(job["vector"]))
                similarity_score = cosine_similarity([resume_vector], [job_vector])[0][0]
                similarity_scores.append(round(similarity_score * 100, 2))
            
            avg_score = round(sum(similarity_scores) / len(similarity_scores), 2) if similarity_scores else 0
            
            sql = "INSERT INTO applications (name, email, resume, job_id, vector, score) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (name, email, file_path, job_id, resume_vector_str, avg_score))
        
        conn.commit()
        return jsonify({
            "message": "Application submitted successfully!",
            "job_id": job_id,
            "average_score": avg_score
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
@app.route("/generate_review", methods=["POST"])
def generate_review_endpoint():
    data = request.get_json()
    email = data.get("email")  # Get email from the request

    if not email:
        print("Email is required")  # Debugging
        return jsonify({"error": "Email is required"}), 400

    conn = get_db_connection()
    if not conn:
        print("Database connection failed!")  # Debugging
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            # Fetch the resume file path using the email
            cursor.execute("SELECT resume FROM applications WHERE email = %s", (email,))
            application = cursor.fetchone()
            
            if not application:
                print("Application not found for email:", email)  # Debugging
                return jsonify({"error": "Application not found for the given email"}), 404
            
            resume_path = application["resume"]
            print("Resume path:", resume_path)  # Debugging
            
            # Extract text from the resume PDF
            resume_text = extract_text_from_pdf(resume_path)
            if not resume_text:
                print("Failed to extract text from resume")  # Debugging
                return jsonify({"error": "Failed to extract text from resume"}), 400
            
            # Generate suggestions for improving the resume
            suggestions = generate_review(resume_text)
            print("Generated suggestions:", suggestions)  # Debugging
            
            return jsonify({"suggestions": suggestions})
    except Exception as e:
        print("Error in generate_review_endpoint:", e)  # Debugging
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/rank_users/<int:job_id>", methods=["GET"])
def rank_users(job_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT vector FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({"message": "Job not found"}), 404
            
            job_vector = np.array(json.loads(job["vector"]))
            
            cursor.execute("SELECT id, name, vector FROM applications WHERE job_id = %s", (job_id,))
            users = cursor.fetchall()
            
            if not users:
                return jsonify({"message": "No applications found"}), 404
    
            ranked_users = [
                {"id": user["id"], "name": user["name"], "score": round(cosine_similarity([job_vector], [np.array(json.loads(user["vector"]))])[0][0] * 100, 2)}
                for user in users
            ]
            
            ranked_users.sort(key=lambda x: x["score"], reverse=True)
            return jsonify(ranked_users)
    finally:
        conn.close()

@app.route('/top_users', methods=['GET'])
def get_top_users():
    """Fetch all users along with their job titles, sorted by highest score."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.name, a.email, a.score, j.title
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                ORDER BY a.score DESC;
            """)
            users = cursor.fetchall()  # Fetch all users

        if users:
            return jsonify(users)

        return jsonify({"message": "No applications found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

#----------------------------------------------------------
def parse_search_query(search_query):
    """
    Parse a natural language search query to extract structured criteria
    Returns a dictionary of recognized patterns and conditions
    """
    search_query = search_query.lower().strip()
    criteria = {
        'score_filter': None,
        'job_title_filter': None,
        'name_filter': None,
        'email_filter': None,
        'sort_order': None,
        'limit': None
    }
    
    # Extract score criteria
    import re
    
    # Score greater than pattern
    score_gt_matches = re.findall(r'score (?:greater than|>|above|more than) (\d+(?:\.\d+)?)', search_query)
    if score_gt_matches:
        criteria['score_filter'] = {'op': '>', 'value': float(score_gt_matches[0])}
    
    # Score less than pattern
    score_lt_matches = re.findall(r'score (?:less than|<|below|under) (\d+(?:\.\d+)?)', search_query)
    if score_lt_matches:
        criteria['score_filter'] = {'op': '<', 'value': float(score_lt_matches[0])}
    
    # Score equals pattern
    score_eq_matches = re.findall(r'score (?:equals|=|is) (\d+(?:\.\d+)?)', search_query)
    if score_eq_matches:
        criteria['score_filter'] = {'op': '=', 'value': float(score_eq_matches[0])}
    
    # Job title patterns
    title_exact_matches = re.findall(r'(?:job title|title) (?:is|=) ["\']([\w\s]+)["\']', search_query)
    if title_exact_matches:
        criteria['job_title_filter'] = {'op': '=', 'value': title_exact_matches[0].strip()}
    else:
        title_matches = re.findall(r'(?:job title|title) (?:is|=|contains) ([\w\s]+)', search_query)
        if title_matches:
            criteria['job_title_filter'] = {'op': 'LIKE', 'value': title_matches[0].strip()}
        elif "software eng" in search_query:
            criteria['job_title_filter'] = {'op': 'LIKE', 'value': "software eng"}
        elif "database" in search_query or " db " in search_query:
            criteria['job_title_filter'] = {'op': 'LIKE', 'value': "db"}
    
    # Name patterns
    name_exact_matches = re.findall(r'name (?:is|=) ["\']([\w\s]+)["\']', search_query)
    if name_exact_matches:
        criteria['name_filter'] = {'op': '=', 'value': name_exact_matches[0].strip()}
    else:
        name_matches = re.findall(r'(?:name|applicant|candidate) (?:is|named|called|=|contains) ([\w\s]+)', search_query)
        if name_matches:
            criteria['name_filter'] = {'op': 'LIKE', 'value': name_matches[0].strip()}
    
    # Email patterns
    email_exact_matches = re.findall(r'email\s*(?:is|=)\s*["\']*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']*', search_query)
    if email_exact_matches:
        criteria['email_filter'] = {'op': '=', 'value': email_exact_matches[0].strip()}
    else:
        email_contains_matches = re.findall(r'email (?:contains|has|with) ([\w\@\.\-]+)', search_query)
        if email_contains_matches:
            criteria['email_filter'] = {'op': 'LIKE', 'value': email_contains_matches[0].strip()}
    
    # Look for "and email = X" pattern specifically
    if "and email" in search_query:
        email_and_matches = re.findall(r'and email\s*(?:is|=)\s*["\']*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']*', search_query)
        if email_and_matches:
            criteria['email_filter'] = {'op': '=', 'value': email_and_matches[0].strip()}
    
    # Sort order
    if any(term in search_query for term in ["highest score", "top score", "best score", "order by score desc"]):
        criteria['sort_order'] = "score DESC"
    elif any(term in search_query for term in ["lowest score", "worst score", "order by score asc"]):
        criteria['sort_order'] = "score ASC"
    elif "order by name" in search_query:
        criteria['sort_order'] = "a.name ASC"
    
    # Limit results
    limit_matches = re.findall(r'(?:top|first|limit) (\d+)', search_query)
    if limit_matches:
        criteria['limit'] = int(limit_matches[0])
    
    # Check for composite queries like "software engineers with score above 20"
    if "software eng" in search_query and "score" in search_query and criteria['job_title_filter'] is None:
        criteria['job_title_filter'] = {'op': 'LIKE', 'value': "software eng"}
    
    print(f"Parsed criteria: {criteria}")
    return criteria


def build_sql_from_criteria(criteria):
    """
    Build an SQL query from structured criteria
    """
    base_sql = """
    SELECT a.name, a.email, a.score, j.title 
    FROM applications a 
    JOIN jobs j ON a.job_id = j.id
    """
    
    where_clauses = []
    
    # Add score filter
    if criteria['score_filter']:
        where_clauses.append(f"a.score {criteria['score_filter']['op']} {criteria['score_filter']['value']}")
    
    # Add job title filter
    if criteria['job_title_filter']:
        if isinstance(criteria['job_title_filter'], dict):
            if criteria['job_title_filter']['op'] == '=':
                where_clauses.append(f"j.title = '{criteria['job_title_filter']['value']}'")
            else:
                where_clauses.append(f"j.title LIKE '%{criteria['job_title_filter']['value']}%'")
        else:
            where_clauses.append(f"j.title LIKE '%{criteria['job_title_filter']}%'")
    
    # Add name filter
    if criteria['name_filter']:
        if isinstance(criteria['name_filter'], dict):
            if criteria['name_filter']['op'] == '=':
                where_clauses.append(f"a.name = '{criteria['name_filter']['value']}'")
            else:
                where_clauses.append(f"a.name LIKE '%{criteria['name_filter']['value']}%'")
        else:
            where_clauses.append(f"a.name LIKE '%{criteria['name_filter']}%'")
    
    # Add email filter
    if criteria['email_filter']:
        if isinstance(criteria['email_filter'], dict):
            if criteria['email_filter']['op'] == '=':
                where_clauses.append(f"a.email = '{criteria['email_filter']['value']}'")
            else:
                where_clauses.append(f"a.email LIKE '%{criteria['email_filter']['value']}%'")
        else:
            where_clauses.append(f"a.email LIKE '%{criteria['email_filter']}%'")
    
    # Construct WHERE clause
    if where_clauses:
        sql_query = f"{base_sql} WHERE {' AND '.join(where_clauses)}"
    else:
        sql_query = base_sql
    
    # Add ORDER BY clause
    if criteria['sort_order']:
        sql_query += f" ORDER BY {criteria['sort_order']}"
    
    # Add LIMIT clause
    if criteria['limit']:
        sql_query += f" LIMIT {criteria['limit']}"
    
    return sql_query


def generate_sql_from_text(query_text):
    """Convert natural language to SQL using Gemini with proper schema info"""
    
    # Define the complete database schema
    schema_info = """
    Database schema:
    1. applications table:
       - id (int, primary key, auto_increment)
       - name (varchar(255), NOT NULL)
       - email (varchar(255), NOT NULL)
       - resume (varchar(500), NOT NULL)
       - job_id (int, NOT NULL)
       - vector (text, NOT NULL)
       - submitted_at (timestamp, default CURRENT_TIMESTAMP)
       - match_score (float, default 0)
       - score (float, default 0)
    
    2. jobs table:
       - id (int, primary key, auto_increment)
       - title (varchar(255))
       - description (text)
       - vector (text)
    
    3. users table:
       - id (int, primary key, auto_increment)
       - name (varchar(255))
       - email (varchar(255))
       - resume (varchar(255))
       - vector (text)
    """
    
    # Create a detailed prompt for Gemini
    prompt = f"""
    You are an SQL expert. Convert the following natural language query into a valid SQL query.
    
    {schema_info}
    
    Natural language query: {query_text}
    
    IMPORTANT GUIDELINES:
    1. When users mention "score", they are referring to the "score" field in the applications table, NOT "match_score".
    2. If the query involves numeric comparisons (like "greater than", "less than", etc.), ensure you include proper WHERE clauses.
    3. For filtering on scores, always add the condition directly to the applications table column (e.g., "WHERE applications.score > 20").
    4. The score is stored as a numeric value (NOT as a percentage string).
    5. Always include a JOIN with the jobs table to get the job title.
    6. Return the name, email, score, and job title in the results.
    7. Return ONLY the SQL query without any explanation or additional text.
    
    Your SQL query should always select at minimum: applications.name, applications.email, applications.score, jobs.title
    """
    
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    
    # Extract just the SQL query
    sql_query = response.text.strip()
    
    # Basic safety check to ensure it's a SELECT query
    if not sql_query.lower().startswith("select"):
        # Use a safe default query if model fails
        return """
        SELECT a.name, a.email, a.score, j.title 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id
        """
    
    return sql_query


@app.route("/search_applicants", methods=["POST"])
def search_applicants():
    try:
        data = request.get_json()
        search_query = data.get("query", "").strip()
        
        if not search_query:
            return jsonify({"error": "Search query is required"}), 400
        
        print(f"Processing search query: {search_query}")
        
        # First try our pattern-based approach
        criteria = parse_search_query(search_query)
        
        # Check if we recognized any patterns
        if any(value is not None for value in criteria.values()):
            # We recognized some patterns, build SQL directly
            sql_query = build_sql_from_criteria(criteria)
            print(f"Using pattern-based SQL: {sql_query}")
        else:
            # Fall back to Gemini for complex queries
            sql_query = generate_sql_from_text(search_query)
            print(f"Using AI-generated SQL: {sql_query}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed!"}), 500

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                
                # Apply post-processing filters for safety
                if criteria['score_filter'] and criteria['score_filter']['op'] == '>':
                    threshold = criteria['score_filter']['value']
                    results = [r for r in results if float(r.get('score', 0)) > threshold]
                
                if criteria['job_title_filter']:
                    if isinstance(criteria['job_title_filter'], dict):
                        job_title = criteria['job_title_filter']['value'].lower()
                        if criteria['job_title_filter']['op'] == '=':
                            results = [r for r in results if job_title == str(r.get('title', '')).lower()]
                        else:
                            results = [r for r in results if job_title in str(r.get('title', '')).lower()]
                    else:
                        job_title = criteria['job_title_filter'].lower()
                        results = [r for r in results if job_title in str(r.get('title', '')).lower()]
                
                if criteria['name_filter']:
                    if isinstance(criteria['name_filter'], dict):
                        name = criteria['name_filter']['value'].lower()
                        if criteria['name_filter']['op'] == '=':
                            results = [r for r in results if name == str(r.get('name', '')).lower()]
                        else:
                            results = [r for r in results if name in str(r.get('name', '')).lower()]
                    else:
                        name = criteria['name_filter'].lower()
                        results = [r for r in results if name in str(r.get('name', '')).lower()]
                
                if criteria['email_filter']:
                    if isinstance(criteria['email_filter'], dict):
                        email = criteria['email_filter']['value'].lower()
                        if criteria['email_filter']['op'] == '=':
                            results = [r for r in results if email == str(r.get('email', '')).lower()]
                        else:
                            results = [r for r in results if email in str(r.get('email', '')).lower()]
                    else:
                        email = criteria['email_filter'].lower()
                        results = [r for r in results if email in str(r.get('email', '')).lower()]
                
                return jsonify(results)
        except Exception as e:
            print(f"SQL execution error: {e}")
            print(f"SQL query was: {sql_query}")
            return jsonify({"error": f"SQL query error: {str(e)}"}), 500
        finally:
            conn.close()
    except Exception as e:
        print(f"General error: {e}")
        return jsonify({"error": str(e)}), 500


# Add this route to your Flask application

@app.route("/delete_job/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        # First check if the job exists
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({"error": "Job not found"}), 404
            
            # Delete any applications related to this job first to maintain referential integrity
            cursor.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
            
            # Then delete the job
            cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            
        conn.commit()
        return jsonify({"message": f"Job (ID: {job_id}) deleted successfully"}), 200
    except Exception as e:
        conn.rollback()  # Rollback changes if an error occurs
        print("Error deleting job:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/manage_jobs")
def manage_jobs():
    # This route will render a template that displays all jobs with delete buttons
    return render_template("manage_jobs.html")

@app.route("/get_all_jobs")
def get_all_jobs():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed!"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, description FROM jobs")
            jobs = cursor.fetchall()
            
        return jsonify(jobs)
    except Exception as e:
        print("Error fetching jobs:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

        


# ------------------ RUN APP ------------------
if __name__ == "__main__":
    app.run(debug=True)