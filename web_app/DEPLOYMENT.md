# DigitalOcean App Platform Deployment Guide

## Prerequisites

1. **DigitalOcean Account**: Sign up at [digitalocean.com](https://digitalocean.com)
2. **doctl CLI**: Install the DigitalOcean CLI tool
   ```bash
   # macOS
   brew install doctl
   
   # Linux
   snap install doctl
   
   # Or download from: https://github.com/digitalocean/doctl/releases
   ```

3. **GitHub Repository**: Push your code to GitHub

## Deployment Steps

### 1. Authenticate with DigitalOcean
```bash
doctl auth init
# Enter your DigitalOcean API token when prompted
```

### 2. Create App Specification
The `.do/app.yaml` file is already configured. Key settings:
- **Source**: GitHub repository
- **Runtime**: Python 3.11
- **Port**: 8080 (automatically set by DigitalOcean)
- **Environment**: PYTHONPATH includes `/workspace/src`

### 3. Deploy the App
```bash
# Navigate to the web_app directory
cd web_app

# Create the app (first time only)
doctl apps create --spec .do/app.yaml

# For subsequent deployments
doctl apps create-deployment <app-id>
```

### 4. Alternative: Manual Deployment via Dashboard

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Select the `web_app` folder as the source directory
5. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `PYTHONPATH`: `/workspace/src`

## Troubleshooting

### "deploy cluster proxy not ready" Error

This error typically occurs due to:

1. **Import Issues**: The app can't find the `deck_compress` module
2. **File Structure**: Incorrect directory structure in deployment
3. **Dependencies**: Missing system dependencies

### Solutions

1. **Check Logs**:
   ```bash
   doctl apps logs <app-id> --follow
   ```

2. **Verify File Structure**: Ensure the deployment includes:
   ```
   web_app/
   ├── main.py
   ├── requirements.txt
   ├── static/
   ├── templates/
   └── .do/app.yaml
   
   src/
   └── deck_compress.py
   ```

3. **Test Locally with Docker**:
   ```bash
   cd web_app
   docker build -t deck-compress-web .
   docker run -p 8080:8080 deck-compress-web
   ```

4. **Check Environment Variables**:
   - `PYTHONPATH` should include the path to `src` directory
   - `PORT` should be set to 8080

## File Structure for Deployment

```
deck-compress/
├── src/
│   └── deck_compress.py
├── web_app/
│   ├── main.py
│   ├── requirements.txt
│   ├── static/
│   ├── templates/
│   ├── .do/
│   │   └── app.yaml
│   └── Dockerfile
└── .gitignore
```

## Environment Variables

- `PORT`: Automatically set by DigitalOcean (usually 8080)
- `PYTHONPATH`: Set to `/workspace/src` to find the deck_compress module

## Monitoring

- **Logs**: `doctl apps logs <app-id> --follow`
- **Status**: `doctl apps get <app-id>`
- **Metrics**: Available in the DigitalOcean dashboard

## Common Issues

1. **Module Not Found**: Ensure `PYTHONPATH` includes the src directory
2. **Static Files 404**: Check that static files are properly mounted
3. **Port Issues**: Use `$PORT` environment variable, not hardcoded port
4. **Memory Issues**: Consider upgrading to a larger instance size

## Support

If you continue to have issues:
1. Check the DigitalOcean App Platform documentation
2. Review the application logs
3. Test the Docker container locally first
4. Contact DigitalOcean support
