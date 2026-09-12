# backend/services/qr_service.py

import qrcode
import boto3
import io
import os
from botocore.exceptions import ClientError
from models.registration import Registration
from extensions import db


class QRService:

    # ──────────────────────────────────────────────────
    # S3 CLIENT
    # ──────────────────────────────────────────────────
    @staticmethod
    def _get_s3_client():
        return boto3.client(
            "s3",
            region_name          = os.getenv("AWS_REGION", "ap-south-1"),
            aws_access_key_id    = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key= os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    # ──────────────────────────────────────────────────
    # GENERATE QR IMAGE (in memory)
    # ──────────────────────────────────────────────────
    @staticmethod
    def _build_qr_image(qr_token):
        """Generate QR PNG in memory. Returns BytesIO buffer."""
        qr = qrcode.QRCode(
            version          = 1,
            error_correction = qrcode.constants.ERROR_CORRECT_H,
            box_size         = 10,
            border           = 4,
        )
        qr.add_data(qr_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    # ──────────────────────────────────────────────────
    # UPLOAD TO S3
    # ──────────────────────────────────────────────────
    @staticmethod
    def _upload_to_s3(buf, s3_key):
        """
        Upload PNG buffer to S3.
        Returns public URL string or raises exception.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        region = os.getenv("AWS_REGION", "ap-south-1")

        client = QRService._get_s3_client()
        client.upload_fileobj(
            buf,
            bucket,
            s3_key,
            ExtraArgs={
                "ContentType": "image/png",
                # Remove ACL if bucket blocks public ACLs
                # Use presigned URLs instead (see get_qr_url)
            }
        )

        # Construct URL
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        return url

    # ──────────────────────────────────────────────────
    # PRESIGNED URL (recommended — works with private buckets)
    # ──────────────────────────────────────────────────
    @staticmethod
    def get_presigned_url(s3_key, expiry_seconds=3600):
        """
        Generate a presigned URL for a private S3 object.
        Default expiry = 1 hour.
        Use this instead of public URLs for security.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        client = QRService._get_s3_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params    = {"Bucket": bucket, "Key": s3_key},
                ExpiresIn = expiry_seconds,
            )
            return url, None
        except ClientError as e:
            return None, str(e)

    # ──────────────────────────────────────────────────
    # GENERATE + UPLOAD (called at registration time)
    # ──────────────────────────────────────────────────
    @staticmethod
    def generate_and_upload(registration):
        """
        Main method — called once at registration time.
        1. Build QR image from qr_token
        2. Upload to S3
        3. Return S3 key (stored in DB as qr_s3_key)

        We store the S3 key, not the URL.
        URL is generated fresh via presigned URL on each request.
        """
        try:
            s3_key = f"qr/{registration.event_id}/{registration.user_id}_{registration.qr_token}.png"

            buf = QRService._build_qr_image(registration.qr_token)
            QRService._upload_to_s3(buf, s3_key)

            return s3_key, None

        except ClientError as e:
            return None, f"S3 upload failed: {str(e)}"
        except Exception as e:
            return None, f"QR generation failed: {str(e)}"

    # ──────────────────────────────────────────────────
    # GET QR URL FOR PARTICIPANT (called when they view QR)
    # ──────────────────────────────────────────────────
    @staticmethod
    def get_qr_url(registration):
        """
        Returns a fresh presigned URL for the QR image.
        If qr_s3_key is missing → regenerate and upload first.
        """
        if not registration.qr_s3_key:
            s3_key, err = QRService.generate_and_upload(registration)
            if err:
                return None, err
            registration.qr_s3_key = s3_key
            db.session.commit()

        url, err = QRService.get_presigned_url(registration.qr_s3_key)
        if err:
            return None, err

        return url, None

    # ──────────────────────────────────────────────────
    # VALIDATE TOKEN (used by volunteer scanner)
    # ──────────────────────────────────────────────────
    @staticmethod
    def validate_token(qr_token):
        """
        Volunteer scans QR → validates token → returns registration.
        Token is the UUID stored in qr_token column.
        """
        reg = Registration.query.filter_by(
            qr_token = qr_token,
            status   = "registered"
        ).first()

        if not reg:
            return None, "Invalid or cancelled QR token"

        return reg, None