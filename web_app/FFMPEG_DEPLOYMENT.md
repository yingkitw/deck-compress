# FFmpeg Deployment Fix

## Issue
The deployed app on DigitalOcean is missing `ffmpeg`, which is required for video compression. This causes the error:
```
Error: ffmpeg not found. Please install ffmpeg to compress videos.
```

## Solution
Updated the deployment configuration to use Docker with ffmpeg pre-installed.

## Files Updated

### 1. Dockerfile
- Added `ffmpeg` to the system dependencies
- Ensures ffmpeg is available in the container

### 2. .do/app.yaml
- Changed from Python environment to Docker deployment
- Uses the updated Dockerfile with ffmpeg

### 3. Code Improvements
- Added graceful handling when ffmpeg is not available
- Better error messages and warnings
- App continues to work for image compression even without ffmpeg

## Deployment Steps

### Option 1: Redeploy via DigitalOcean Dashboard
1. Go to your DigitalOcean App Platform dashboard
2. Find your `deck-compress-web-app`
3. Go to Settings → App Spec
4. Replace the current app.yaml with the updated version
5. Click "Save" and the app will redeploy automatically

### Option 2: Redeploy via CLI (if you have doctl)
```bash
# Update the app with the new configuration
doctl apps update <your-app-id> --spec web_app/.do/app.yaml
```

### Option 3: Manual Update
1. Copy the updated `.do/app.yaml` content
2. Paste it into your DigitalOcean App Platform app spec
3. Save and redeploy

## Verification
After deployment, test with a PowerPoint file containing videos:
1. Upload a .pptx file with embedded videos
2. Check the logs for ffmpeg availability
3. Videos should now compress successfully

## Fallback Behavior
If ffmpeg is still not available:
- Image compression will work normally
- Video compression will be skipped with a warning
- The app will continue to function for other file types

## Expected Logs After Fix
```
POST /upload/ - File: presentation.pptx, Size: 1234567
Processing media1.mov (1/5) - 74.1MB...
✓ Video compressed: 45.2% reduction
Processing media2.jpg (2/5) - 2.1MB...
✓ Image compressed: 30.1% reduction
```
