# 🚀 AgentHub Registry Deployment Guide

This guide walks you through deploying the AgentHub Registry backend to Render.com with PostgreSQL, Redis, and AWS S3.

## 📋 Prerequisites

Before deploying, ensure you have:

1. **GitHub Repository** - Your code pushed to GitHub
2. **Render.com Account** - Sign up at [render.com](https://render.com)
3. **AWS Account** - For S3 bucket creation
4. **GitHub OAuth App** - For authentication

## 🗂️ AWS S3 Setup

### 1. Create S3 Bucket

```bash
# Create bucket (replace with your bucket name)
aws s3 mb s3://agenthub-registry-packages --region us-east-1

# Set bucket policy for public read access
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::agenthub-registry-packages/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket agenthub-registry-packages --policy file://bucket-policy.json
```

### 2. Create IAM User

```bash
# Create IAM user for registry
aws iam create-user --user-name agenthub-registry

# Create access key
aws iam create-access-key --user-name agenthub-registry

# Attach S3 policy
cat > s3-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::agenthub-registry-packages",
                "arn:aws:s3:::agenthub-registry-packages/*"
            ]
        }
    ]
}
EOF

aws iam put-user-policy --user-name agenthub-registry --policy-name S3Access --policy-document file://s3-policy.json
```

Save the Access Key ID and Secret Access Key for later.

## 🔐 GitHub OAuth Setup

### 1. Create GitHub OAuth App

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: AgentHub Registry
   - **Homepage URL**: `https://registry.agenthubcli.com`
   - **Authorization callback URL**: `https://registry.agenthubcli.com/api/v1/auth/github/callback`
4. Save Client ID and Client Secret

## 🏗️ Render.com Deployment

### 1. Connect GitHub Repository

1. Login to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" > "Blueprint"
3. Connect your GitHub repository
4. Select the repository containing your AgentHub Registry code

### 2. Configure Blueprint Deployment

Render will automatically detect the `render.yaml` file and create:

- Web Service (API)
- PostgreSQL Database
- Redis Instance

### 3. Set Environment Variables

After the initial deployment, set these environment variables in the Render dashboard:

#### AWS S3 Configuration

```
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=agenthub-registry-packages
```

#### GitHub OAuth

```
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### Optional Monitoring

```
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 4. Custom Domain (Optional)

1. In Render dashboard, go to your web service
2. Click "Settings" > "Custom Domains"
3. Add `registry.agenthubcli.com`
4. Configure DNS:
   ```
   Type: CNAME
   Name: registry
   Value: your-service-name.onrender.com
   ```

## 🔧 Database Migrations

The database tables will be created automatically on first startup. If you need to run migrations manually:

```python
# In the app startup, tables are created via:
await create_tables()
```

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- **Basic**: `GET /health`
- **Detailed**: `GET /api/v1/health/detailed`
- **Metrics**: `GET /metrics` (Prometheus format)

### Set Up Monitoring

1. **Uptime Monitoring**: Use Render's built-in health checks
2. **Error Tracking**: Configure Sentry DSN in environment variables
3. **Metrics**: Set up Prometheus scraping if needed

## 🚦 Production Checklist

### Security

- [ ] Environment variables properly set
- [ ] S3 bucket permissions configured
- [ ] HTTPS enabled (automatic with Render)
- [ ] Rate limiting configured
- [ ] Security headers enabled

### Performance

- [ ] Database connection pooling configured
- [ ] Redis caching enabled
- [ ] Static file serving optimized
- [ ] CDN setup (optional)

### Monitoring

- [ ] Health checks working
- [ ] Error tracking configured
- [ ] Log aggregation setup
- [ ] Metrics collection enabled

## 📖 API Documentation

Once deployed, your API documentation will be available at:

- **Interactive Docs**: `https://your-domain/docs` (development only)
- **ReDoc**: `https://your-domain/redoc` (development only)
- **OpenAPI Schema**: `https://your-domain/api/v1/openapi.json`

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**

   - Check DATABASE_URL environment variable
   - Verify PostgreSQL service is running

2. **S3 Upload Errors**

   - Verify AWS credentials
   - Check S3 bucket permissions
   - Ensure bucket exists in correct region

3. **GitHub OAuth Not Working**

   - Verify callback URL matches exactly
   - Check client ID and secret
   - Ensure OAuth app is active

4. **High Memory Usage**
   - Monitor database connection pool size
   - Check for memory leaks in application logs
   - Consider upgrading Render plan

### Debug Commands

```bash
# Check service logs
curl https://your-service.onrender.com/health

# Test database connection
curl https://your-service.onrender.com/api/v1/health/detailed

# View application metrics
curl https://your-service.onrender.com/metrics
```

## 📈 Scaling Considerations

### Database

- Start with Render's Starter PostgreSQL plan
- Upgrade to Standard for production traffic
- Consider read replicas for heavy read workloads

### Redis

- Starter plan sufficient for caching
- Monitor memory usage and upgrade if needed

### Web Service

- Standard plan supports moderate traffic
- Pro plan for high-traffic production use
- Consider horizontal scaling for very high loads

### S3

- Standard S3 pricing applies
- Enable CloudFront CDN for global distribution
- Set up lifecycle policies for old package versions

## 🔄 CI/CD Pipeline

Render automatically deploys on git push to main branch. For advanced workflows:

### GitHub Actions (Optional)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Render
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

## 📞 Support

For deployment issues:

1. Check Render service logs
2. Review this deployment guide
3. Check the health endpoints
4. Open an issue in the GitHub repository

---

🎉 **Congratulations!** Your AgentHub Registry is now deployed and ready to serve millions of AI developers worldwide!

Access your registry at: `https://registry.agenthubcli.com`
