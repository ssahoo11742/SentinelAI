"""
Test script to upload a CSV file to Supabase storage
Usage: python test_upload.py <csv_filename>
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = "https://uxrdywchpcwljsteomtn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4cmR5d2NocGN3bGpzdGVvbXRuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjEyMDUzMywiZXhwIjoyMDc3Njk2NTMzfQ.jaQvrFqm4wTOyS_XxaUzCM1REtEyh-9Sj1EDFNjKJ8g"
STORAGE_BUCKET = "sentinel_reports"

def test_upload(csv_filename: str):
    """Test uploading a CSV file to Supabase storage"""
    
    print("=" * 60)
    print("🧪 SUPABASE STORAGE UPLOAD TEST")
    print("=" * 60)
    
    # Verify environment
    print(f"\n📋 Configuration:")
    print(f"   Supabase URL: {SUPABASE_URL}")
    print(f"   API Key (first 20 chars): {SUPABASE_KEY[:20] if SUPABASE_KEY else 'NOT SET'}")
    print(f"   Storage Bucket: {STORAGE_BUCKET}")
    print(f"   CSV File: {csv_filename}")
    
    if not SUPABASE_KEY:
        print("\n❌ ERROR: SUPABASE_KEY not found in environment variables!")
        print("   Make sure you have a .env file with SUPABASE_KEY set")
        return False
    
    # Check if file exists
    if not os.path.exists(csv_filename):
        print(f"\n❌ ERROR: File '{csv_filename}' not found!")
        return False
    
    file_size = os.path.getsize(csv_filename)
    print(f"   File size: {file_size:,} bytes")
    
    # Initialize Supabase client
    print("\n🔌 Connecting to Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("   ✅ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # Prepare upload
    storage_filename = f"test_{os.path.basename(csv_filename)}"
    print(f"\n📤 Uploading as: {storage_filename}")
    
    try:
        # Upload the file
        with open(csv_filename, "rb") as f:
            result = supabase.storage.from_(STORAGE_BUCKET).upload(
                storage_filename,
                f,
                file_options={"content-type": "text/csv"}
            )
        
        print(f"   ✅ Upload successful!")
        print(f"   Storage path: {STORAGE_BUCKET}/{storage_filename}")
        
        # Get public URL
        try:
            public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_filename)
            print(f"   🌐 Public URL: {public_url}")
        except Exception as e:
            print(f"   ⚠️  Could not get public URL: {e}")
        
        print("\n" + "=" * 60)
        print("✅ TEST PASSED - Upload successful!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"   ❌ Upload failed!")
        print(f"\n💥 ERROR DETAILS:")
        print(f"   {str(e)}")
        
        # Try to parse the error
        if "403" in str(e) or "Unauthorized" in str(e):
            print("\n🔍 DIAGNOSIS:")
            print("   This is a permissions error. Possible causes:")
            print("   1. You're using the 'anon' key instead of 'service_role' key")
            print("   2. RLS policies on the bucket are blocking the upload")
            print("   3. The API key doesn't have storage permissions")
            print("\n💡 SOLUTIONS:")
            print("   1. Use the service_role key from Supabase dashboard")
            print("   2. Check Storage policies in Supabase dashboard")
            print("   3. Make sure the bucket exists and is accessible")
        
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_upload.py <csv_filename>")
        print("Example: python test_upload.py test.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    success = test_upload(csv_file)
    sys.exit(0 if success else 1)