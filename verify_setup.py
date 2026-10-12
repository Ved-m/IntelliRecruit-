#!/usr/bin/env python3
"""
Setup verification script for Job Recommendation System
Checks all requirements and configurations
"""

import os
import sys
import json
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python 3.8+ required. You have {version.major}.{version.minor}")
        return False

def check_env_file():
    """Check .env file exists"""
    print("\n🔍 Checking .env file...")
    if os.path.exists('.env'):
        print("✅ .env file found")
        # Check required keys
        with open('.env', 'r') as f:
            content = f.read()
        
        required_keys = [
            'FIREBASE_API_KEY',
            'FIREBASE_PROJECT_ID',
            'DB_HOST',
            'DB_USER',
            'DB_PASSWORD',
            'DB_NAME',
            'PINECONE_API_KEY',
            'GENAI_API_KEY'
        ]
        
        missing = [k for k in required_keys if k not in content]
        if missing:
            print(f"⚠️  Missing environment variables: {missing}")
            print("   Update .env with all required values")
            return False
        else:
            print("✅ All required environment variables present")
            return True
    else:
        print("❌ .env file not found")
        print("   Create .env file with required credentials")
        return False

def check_firebase_key():
    """Check Firebase key file"""
    print("\n🔍 Checking Firebase configuration...")
    if os.path.exists('firebase-key.json'):
        print("✅ firebase-key.json found")
        try:
            with open('firebase-key.json', 'r') as f:
                key = json.load(f)
            if 'project_id' in key and 'private_key' in key:
                print(f"✅ Valid Firebase key for project: {key['project_id']}")
                return True
            else:
                print("❌ Invalid Firebase key structure")
                return False
        except Exception as e:
            print(f"❌ Error reading Firebase key: {e}")
            return False
    else:
        print("❌ firebase-key.json not found")
        print("   Download from Firebase Console > Project Settings > Service Accounts")
        return False

def check_requirements():
    """Check if required packages installed"""
    print("\n🔍 Checking Python packages...")
    
    required_packages = [
        'flask',
        'pymysql',
        'firebase_admin',
        'pinecone',
        'sentence_transformers',
        'sklearn',
        'google.generativeai',
        'dotenv'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {missing}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All packages installed")
    return True

def check_database():
    """Check database connection"""
    print("\n🔍 Checking MySQL database...")
    try:
        import pymysql
        from dotenv import load_dotenv
        
        load_dotenv()
        
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '123456'),
            database=os.getenv('DB_NAME', 'job_db')
        )
        
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        required_tables = ['users', 'jobs', 'applications']
        missing_tables = [t for t in required_tables if t not in table_names]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            print("   Run: mysql -u root -p123456 < database.sql")
            cursor.close()
            conn.close()
            return False
        
        print(f"✅ Database connected. Tables found: {', '.join(table_names)}")
        
        # Check schema
        cursor.execute("DESCRIBE users")
        users_schema = cursor.fetchall()
        needed_columns = ['firebase_uid', 'role']
        
        user_columns = [col[0] for col in users_schema]
        missing_cols = [c for c in needed_columns if c not in user_columns]
        
        if missing_cols:
            print(f"⚠️  Missing columns in users table: {missing_cols}")
            print("   Run: mysql -u root -p123456 < database.sql")
            cursor.close()
            conn.close()
            return False
        
        print("✅ Database schema correct")
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("   Ensure MySQL is running and credentials are correct")
        return False

def check_pinecone():
    """Check Pinecone configuration"""
    print("\n🔍 Checking Pinecone...")
    try:
        from dotenv import load_dotenv
        from pinecone import Pinecone
        
        load_dotenv()
        
        api_key = os.getenv('PINECONE_API_KEY')
        index_name = os.getenv('PINECONE_INDEX_NAME', 'job-recommendations')
        
        if not api_key or api_key == 'your_pinecone_api_key':
            print("❌ Pinecone API key not configured")
            print("   Update PINECONE_API_KEY in .env")
            return False
        
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        
        print(f"✅ Pinecone connected to index: {index_name}")
        return True
    
    except Exception as e:
        print(f"⚠️  Pinecone warning (optional for testing): {e}")
        return True  # Don't fail if Pinecone not configured

def run_all_checks():
    """Run all checks"""
    print("=" * 60)
    print("📋 JOB RECOMMENDATION SYSTEM - SETUP VERIFICATION")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_env_file(),
        check_firebase_key(),
        check_requirements(),
        check_database(),
        check_pinecone()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ ALL CHECKS PASSED! Ready to run: python app.py")
    else:
        print("⚠️  SOME CHECKS FAILED. Please review above and fix issues.")
    print("=" * 60)
    
    return all(checks)

if __name__ == '__main__':
    success = run_all_checks()
    sys.exit(0 if success else 1)
