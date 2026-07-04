# Using Cloudflare R2 with sharexd

1. Log in to your Cloudflare dashboard.

2. Select "Storage & databases" > "R2 Object Storage" > "Overview" from the sidebar.

3. Click "+ Create Bucket".

4. Pick a bucket name, leave everything else as the default, and create the bucket.

5. Go back to the overview page, and click "Manage" under "Account Details > API Tokens".

6. Click "Create Account API Token".

7. Set Permissions to "Object Read & Write".

8. Click "Apply to specific buckets only", and select the bucket you just made.

9. In your `.env` file, set `STORAGE_BACKEND` to `s3`

10. Set `S3_BUCKET_NAME` to the bucket you created, `S3_ENDPOINT_URL` to the `.r2.cloudflarestorage.com` URL on the API token screen, `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` to the keys Cloudflare gave you, and `S3_REGION` to `auto`.
