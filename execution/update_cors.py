import boto3
import os
from dotenv import load_dotenv

load_dotenv()

bucket_name = os.getenv("S3_BUCKET_NAME", "vlmcreateflowbucket")

print(f"--- UPDATING CORS FOR: {bucket_name} ---")

s3 = boto3.client(
    's3', 
    region_name=os.getenv("AWS_REGION", "ap-southeast-2")
)

cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST', 'DELETE'],
        'AllowedOrigins': ['*'], # Allow all for Streamlit/Localhost access
        'ExposeHeaders': ['ETag', 'x-amz-request-id']
    }]
}

try:
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
    print("✅ CORS Configuration Applied Successfully!")
except Exception as e:
    print(f"❌ Failed to Apply CORS: {e}")
