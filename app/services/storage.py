"""
S3 storage service for AgentHub Registry package artifacts.
"""

import hashlib
import io
from typing import BinaryIO, Dict, Optional, Tuple

import boto3
import structlog
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from app.core.config import settings

logger = structlog.get_logger()


class S3StorageService:
    """Service for managing package files in AWS S3."""
    
    def __init__(self):
        """Initialize S3 client with configuration."""
        try:
            # Configure S3 client with retry and timeout settings
            config = Config(
                region_name=settings.AWS_REGION,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                connect_timeout=10,
                read_timeout=60,
            )
            
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    config=config
                )
            else:
                # Use IAM role or environment credentials
                self.s3_client = boto3.client('s3', config=config)
                
            self.bucket_name = settings.S3_BUCKET_NAME
            
            # Verify bucket access
            self._verify_bucket_access()
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise ValueError("AWS credentials not configured")
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            raise
    
    def _verify_bucket_access(self) -> None:
        """Verify that we can access the S3 bucket."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info("S3 bucket access verified", bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error("S3 bucket not found", bucket=self.bucket_name)
                raise ValueError(f"S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                logger.error("Access denied to S3 bucket", bucket=self.bucket_name)
                raise ValueError(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error("S3 bucket access error", error=str(e))
                raise
    
    def generate_package_key(self, package_name: str, version: str, filename: str) -> str:
        """Generate S3 key for a package file."""
        # Normalize package name for consistent storage
        normalized_name = package_name.lower().replace("_", "-")
        return f"packages/{normalized_name}/{version}/{filename}"
    
    def calculate_file_hash(self, file_data: bytes) -> str:
        """Calculate SHA256 hash of file data."""
        return hashlib.sha256(file_data).hexdigest()
    
    async def upload_package(
        self,
        file_data: bytes,
        package_name: str,
        version: str,
        filename: str,
        content_type: str = "application/octet-stream"
    ) -> Tuple[str, str, int]:
        """
        Upload a package file to S3.
        
        Returns:
            Tuple of (s3_key, file_hash, file_size)
        """
        try:
            # Generate S3 key
            s3_key = self.generate_package_key(package_name, version, filename)
            
            # Calculate file hash and size
            file_hash = self.calculate_file_hash(file_data)
            file_size = len(file_data)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata={
                    'package-name': package_name,
                    'package-version': version,
                    'filename': filename,
                    'file-hash': file_hash,
                    'uploaded-by': 'agenthub-registry'
                },
                ServerSideEncryption='AES256',
                CacheControl='public, max-age=31536000',  # 1 year cache
            )
            
            logger.info(
                "Package uploaded to S3",
                package=package_name,
                version=version,
                s3_key=s3_key,
                file_size=file_size,
                file_hash=file_hash
            )
            
            return s3_key, file_hash, file_size
            
        except ClientError as e:
            logger.error(
                "Failed to upload package to S3",
                package=package_name,
                version=version,
                error=str(e)
            )
            raise ValueError(f"Failed to upload package: {e}")
        except Exception as e:
            logger.error(
                "Unexpected error uploading package",
                package=package_name,
                version=version,
                error=str(e)
            )
            raise
    
    async def download_package(self, s3_key: str) -> bytes:
        """Download a package file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return response['Body'].read()
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning("Package file not found in S3", s3_key=s3_key)
                raise FileNotFoundError(f"Package file not found: {s3_key}")
            else:
                logger.error("Failed to download package from S3", s3_key=s3_key, error=str(e))
                raise ValueError(f"Failed to download package: {e}")
    
    async def delete_package(self, s3_key: str) -> bool:
        """Delete a package file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info("Package deleted from S3", s3_key=s3_key)
            return True
            
        except ClientError as e:
            logger.error("Failed to delete package from S3", s3_key=s3_key, error=str(e))
            return False
    
    async def get_package_info(self, s3_key: str) -> Optional[Dict]:
        """Get package file information from S3."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                logger.error("Failed to get package info from S3", s3_key=s3_key, error=str(e))
                raise ValueError(f"Failed to get package info: {e}")
    
    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """Generate a presigned URL for package download."""
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            logger.error("Failed to generate presigned URL", s3_key=s3_key, error=str(e))
            raise ValueError(f"Failed to generate download URL: {e}")
    
    async def copy_package(self, source_key: str, dest_key: str) -> bool:
        """Copy a package file within S3."""
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key,
                ServerSideEncryption='AES256',
                MetadataDirective='COPY'
            )
            
            logger.info("Package copied in S3", source=source_key, dest=dest_key)
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to copy package in S3",
                source=source_key,
                dest=dest_key,
                error=str(e)
            )
            return False
    
    async def list_package_versions(self, package_name: str) -> list:
        """List all versions of a package in S3."""
        try:
            normalized_name = package_name.lower().replace("_", "-")
            prefix = f"packages/{normalized_name}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            versions = []
            for prefix_info in response.get('CommonPrefixes', []):
                # Extract version from prefix like "packages/package-name/1.0.0/"
                prefix_path = prefix_info['Prefix']
                version = prefix_path.rstrip('/').split('/')[-1]
                versions.append(version)
            
            return sorted(versions)
            
        except ClientError as e:
            logger.error("Failed to list package versions", package=package_name, error=str(e))
            return []
    
    def get_public_url(self, s3_key: str) -> str:
        """Get public URL for a package file."""
        return f"{settings.s3_public_url}/{s3_key}"


# Global storage service instance
storage_service = S3StorageService() 