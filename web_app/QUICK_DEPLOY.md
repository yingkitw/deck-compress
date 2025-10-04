# Quick Deployment Guide

## Centralized Web App Structure

All code is now centralized in the `web_app/` directory:

```
web_app/
├── main.py              # FastAPI application
├── deck_compress.py     # Core compression logic
├── requirements.txt     # Python dependencies
├── static/             # Static files (CSS, uploads)
├── templates/          # HTML templates
├── .do/
│   └── app.yaml        # DigitalOcean App Platform config
├── Dockerfile          # Docker configuration
└── test_local.py       # Local testing script
```

## Deploy to DigitalOcean

### 1. Update GitHub Repository URL
Edit `.do/app.yaml` and replace `your-username/deck-compress` with your actual GitHub repository.

### 2. Deploy
```bash
# Using doctl CLI
doctl apps create --spec .do/app.yaml

# Or via DigitalOcean Dashboard
# Upload the .do/app.yaml file
```

### 3. Test Locally First
```bash
cd web_app
python test_local.py
python main.py
```

## Key Changes Made

- ✅ **Centralized Code**: All code is now in `web_app/` directory
- ✅ **Simplified Imports**: No more complex path resolution
- ✅ **Removed Dependencies**: No need for `src/` directory or `PYTHONPATH`
- ✅ **Clean Structure**: Everything needed for deployment is in one place

## Troubleshooting

If you still get import errors:
1. Check that `deck_compress.py` is in the same directory as `main.py`
2. Verify all dependencies are in `requirements.txt`
3. Test locally with `python test_local.py`

The app should now deploy successfully to DigitalOcean App Platform!
