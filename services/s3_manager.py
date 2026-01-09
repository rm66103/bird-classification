"""
S3 Storage Manager

This service provides an interface to AWS S3 for storing and retrieving
bird call recordings and metadata. It wraps boto3 operations with
convenient methods for the bird classification project.

AWS credentials should be configured via environment variables or AWS credentials file.
Required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, List, Dict, Any
import os
from pathlib import Path


class S3Manager:
    """Service for interacting with AWS S3 for bird classification data storage."""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        create_bucket_if_not_exists: bool = False
    ):
        """
        Initialize the S3 manager.
        
        Args:
            bucket_name: S3 bucket name. If not provided, reads from S3_BUCKET_NAME env var.
            region: AWS region. If not provided, reads from AWS_REGION env var.
            create_bucket_if_not_exists: If True, create bucket if it doesn't exist (default: False)
        
        Raises:
            ValueError: If bucket_name is not provided and not found in environment
            NoCredentialsError: If AWS credentials are not configured
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        if not self.bucket_name:
            raise ValueError(
                "S3 bucket name is required. "
                "Provide it as a parameter or set S3_BUCKET_NAME environment variable."
            )
        
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.s3_resource = boto3.resource('s3', region_name=self.region)
        except NoCredentialsError:
            raise NoCredentialsError(
                "AWS credentials not found. "
                "Configure credentials via environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) "
                "or AWS credentials file (~/.aws/credentials)."
            )
        
        # Check bucket existence and create if requested
        if create_bucket_if_not_exists:
            self._ensure_bucket_exists()
        else:
            if not self.bucket_exists():
                raise ValueError(f"Bucket '{self.bucket_name}' does not exist. Create it first or set create_bucket_if_not_exists=True.")
    
    def bucket_exists(self) -> bool:
        """
        Check if the bucket exists.
        
        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        if not self.bucket_exists():
            try:
                if self.region == 'us-east-1':
                    # us-east-1 doesn't require LocationConstraint
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                print(f"Created S3 bucket: {self.bucket_name}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'BucketAlreadyOwnedByYou':
                    pass  # Bucket exists, that's fine
                else:
                    raise
    
    def upload_file(
        self,
        local_file_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file to S3.
        
        Args:
            local_file_path: Path to local file to upload
            s3_key: S3 object key (path within bucket)
            metadata: Optional metadata dictionary to attach to the object
        
        Returns:
            True if upload successful, False otherwise
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            return True
        except ClientError as e:
            print(f"Error uploading {local_file_path} to s3://{self.bucket_name}/{s3_key}: {e}")
            return False
        except FileNotFoundError:
            print(f"File not found: {local_file_path}")
            return False
    
    def upload_audio_file(
        self,
        local_file_path: str,
        species_common_name: str,
        recording_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Upload an audio file to S3 with standardized path structure.
        
        Args:
            local_file_path: Path to local audio file
            species_common_name: Common name of the bird species
            recording_id: Xeno-canto recording ID
            metadata: Optional metadata dictionary
        
        Returns:
            S3 URI of uploaded file, or None if upload failed
        """
        # Normalize species name for path (replace spaces with underscores)
        species_path = species_common_name.replace(' ', '_').lower()
        
        # Get file extension
        file_ext = Path(local_file_path).suffix or '.mp3'
        
        # Construct S3 key
        s3_key = f"raw-audio/{species_path}/{recording_id}{file_ext}"
        
        if self.upload_file(local_file_path, s3_key, metadata):
            return f"s3://{self.bucket_name}/{s3_key}"
        return None
    
    def upload_metadata_file(
        self,
        local_file_path: str,
        filename: str = "recordings_metadata"
    ) -> Optional[str]:
        """
        Upload a metadata file (CSV or JSON) to S3.
        
        Args:
            local_file_path: Path to local metadata file
            filename: Base filename (without extension) for S3 storage
        
        Returns:
            S3 URI of uploaded file, or None if upload failed
        """
        file_ext = Path(local_file_path).suffix
        s3_key = f"metadata/{filename}{file_ext}"
        
        if self.upload_file(local_file_path, s3_key):
            return f"s3://{self.bucket_name}/{s3_key}"
        return None
    
    def download_file(self, s3_key: str, local_file_path: str) -> bool:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 object key (path within bucket)
            local_file_path: Local path where file should be saved
        
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            Path(local_file_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_file_path
            )
            return True
        except ClientError as e:
            print(f"Error downloading s3://{self.bucket_name}/{s3_key}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List all files in the bucket with the given prefix.
        
        Args:
            prefix: S3 key prefix to filter by (e.g., "raw-audio/Northern_Cardinal/")
        
        Returns:
            List of S3 keys matching the prefix
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            return [obj['Key'] for obj in response['Contents']]
        except ClientError as e:
            print(f"Error listing files with prefix '{prefix}': {e}")
            return []
    
    def list_species_files(self, species_common_name: str) -> List[str]:
        """
        List all audio files for a specific species.
        
        Args:
            species_common_name: Common name of the bird species
        
        Returns:
            List of S3 keys for that species' audio files
        """
        species_path = species_common_name.replace(' ', '_').lower()
        prefix = f"raw-audio/{species_path}/"
        return self.list_files(prefix)
    
    def get_s3_uri(self, s3_key: str) -> str:
        """
        Get full S3 URI for a given key.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            Full S3 URI (s3://bucket/key)
        """
        return f"s3://{self.bucket_name}/{s3_key}"
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

