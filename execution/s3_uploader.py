import os
import boto3
import mimetypes
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
import uuid

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "vlmcreateflowbucket")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

def upload_file_obj(file_obj, object_name=None):
    """
    Uploads a file-like object to S3.
    """
    if object_name is None:
        object_name = f"uploads/{uuid.uuid4()}_{file_obj.name}"
    
    # Add timeout config to prevent hanging
    from botocore.config import Config
    config = Config(
        connect_timeout=5,
        read_timeout=60,
        retries={'max_attempts': 2}
    )
    
    s3 = boto3.client('s3', region_name=REGION, config=config)
    
    # Reset pointer
    file_obj.seek(0)
    
    content_type, _ = mimetypes.guess_type(object_name)
    if content_type is None:
        content_type = 'binary/octet-stream'
        
    try:
        s3.upload_fileobj(
            file_obj,
            BUCKET_NAME,
            object_name,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Generate Presigned URL (Valid for 1 hour)
        # This resolves 'Video URL is invalid' errors caused by 
        # private buckets or strict ACLs.
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': object_name},
            ExpiresIn=3600
        )
        print(f"DEBUG: Generated Presigned URL: {url}")
        return url
        
    except ClientError as e:
        print(f"S3 Upload Error: {e}")
        return None

def delete_file(object_name):
    """
    Deletes a file from S3.
    """
    if not object_name:
        return False
    
    from botocore.config import Config
    config = Config(
        connect_timeout=5,
        read_timeout=30,
        retries={'max_attempts': 2}
    )
    
    s3 = boto3.client('s3', region_name=REGION, config=config)
    
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=object_name)
        print(f"DEBUG: Deleted from S3: {object_name}")
        return True
    except ClientError as e:
        print(f"S3 Delete Error: {e}")
        return False
