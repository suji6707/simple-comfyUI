# ComfyUI-Like Image Generation Service

A production-ready image generation service inspired by ComfyUI's node-based architecture, featuring template-based workflows, real-time progress tracking, and a modern web interface.

## ✨ Features

- **Template-Based Generation**: Pre-configured workflows for different art styles (Photorealistic, Anime, Oil Painting, 3D Render, etc.)
- **Real-Time Progress Tracking**: Server-Sent Events (SSE) for live generation updates
- **Node-Based Workflow Engine**: ComfyUI-inspired processing pipeline with DAG execution
- **Modern Web Interface**: React/Next.js frontend with responsive design
- **Scalable Architecture**: FastAPI backend with Celery queue system
- **Production Ready**: Docker containerization, monitoring, and comprehensive error handling
- **Image Gallery**: Browse and manage your generated images
- **Batch Processing**: Generate multiple images efficiently

## 🏗️ Architecture

### Frontend (Next.js 15 + TypeScript)
- **Framework**: Next.js with App Router
- **State Management**: Zustand for client state
- **UI Components**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS
- **Real-time Updates**: Server-Sent Events (SSE)

### Backend (FastAPI + Python)
- **API Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Queue System**: Celery with Redis broker
- **Workflow Engine**: Custom node-based processing system
- **Monitoring**: Prometheus metrics and structured logging
- **Storage**: S3-compatible object storage (MinIO for development)

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose
- **Monitoring**: Prometheus metrics, Flower for Celery
- **Development**: Hot reload for both frontend and backend

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd simple-vision
cp .env.example .env
```

### 2. Start Development Environment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start all services
./scripts/start.sh
```

This will start:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/v1/docs
- **Flower (Celery Monitor)**: http://localhost:5555
- **MinIO (S3 Storage)**: http://localhost:9001

### 3. Stop Services

```bash
./scripts/stop.sh
```

## 📖 Usage Guide

### Creating Your First Image

1. **Open the Interface**: Navigate to http://localhost:3000
2. **Choose a Template**: Select from available styles (Photorealistic, Anime, etc.)
3. **Enter Your Prompt**: Describe what you want to generate
4. **Adjust Settings**: Modify resolution, number of images, and advanced parameters
5. **Generate**: Click the generate button and watch real-time progress
6. **View Results**: Browse your generated images in the gallery

### Template System

Templates define pre-configured workflows with:
- **Model Selection**: Automatically choose appropriate AI models
- **Parameter Optimization**: Pre-tuned settings for each style
- **Workflow Definition**: Node-based processing pipeline
- **User Parameters**: Customizable options for each template

### Advanced Features

#### Workflow Engine
- **Node-Based Processing**: ComfyUI-inspired DAG execution
- **Parallel Processing**: Independent nodes run concurrently
- **Error Recovery**: Robust error handling and retry logic
- **Caching**: Intelligent result caching for efficiency

#### Real-Time Updates
- **Progress Tracking**: Live updates during generation
- **Queue Position**: See your place in the processing queue
- **Status Changes**: Immediate feedback on job status

## 🔧 Development

### Local Development Setup

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend Development
```bash
cd frontend
pnpm install
pnpm dev
```

#### Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

#### Running Celery Worker
```bash
cd backend
celery -A app.workers.celery_worker worker --loglevel=info
```

### Project Structure

```
simple-vision/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # Next.js app router pages
│   │   ├── components/      # React components
│   │   │   ├── ui/          # shadcn/ui components
│   │   │   ├── TemplateCard.tsx
│   │   │   ├── GenerationForm.tsx
│   │   │   ├── ProgressTracker.tsx
│   │   │   └── ImageGallery.tsx
│   │   └── lib/
│   │       ├── api-client.ts    # API communication
│   │       ├── utils.ts         # Utility functions
│   │       └── stores/          # Zustand stores
│   ├── package.json
│   └── Dockerfile
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Core configuration and utilities
│   │   │   ├── config.py    # Settings and configuration
│   │   │   ├── workflow_engine.py  # Node-based processing
│   │   │   └── monitoring.py   # Metrics and health checks
│   │   ├── models/          # Database models and schemas
│   │   ├── services/        # Business logic services
│   │   └── workers/         # Celery workers
│   ├── templates/           # Workflow templates
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml       # Container orchestration
├── scripts/                # Utility scripts
│   ├── start.sh            # Development startup
│   └── stop.sh             # Service shutdown
└── README.md
```

## 🔌 API Documentation

### Core Endpoints

#### Templates
- `GET /api/v1/templates` - List all templates
- `GET /api/v1/templates/{id}` - Get specific template
- `GET /api/v1/templates/categories` - Get template categories

#### Generation
- `POST /api/v1/generate` - Submit generation request
- `GET /api/v1/generate/{job_id}/status` - Check job status
- `GET /api/v1/generate/{job_id}/stream` - SSE progress stream
- `GET /api/v1/history` - User's generation history

#### Health & Monitoring
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed component health
- `GET /metrics` - Prometheus metrics

### Example API Usage

#### Submit Generation
```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "uuid-here",
    "prompt": "A beautiful sunset over mountains",
    "parameters": {
      "width": 1024,
      "height": 1024,
      "num_images": 1,
      "steps": 50
    }
  }'
```

#### Check Status
```bash
curl "http://localhost:8000/api/v1/generate/{job_id}/status"
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/comfyui_service

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Storage (S3-compatible)
AWS_BUCKET_NAME=comfyui-images
AWS_REGION=us-east-1
CDN_URL=https://your-cdn-domain.com

# Model Configuration
MODEL_CACHE_DIR=/tmp/models
DEFAULT_MODEL=stabilityai/stable-diffusion-xl-base-1.0

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
```

### Template Configuration

Templates are defined in JSON format with workflow configurations:

```json
{
  "name": "Photorealistic Portrait",
  "description": "Generate high-quality photorealistic human portraits",
  "category": "Portrait",
  "workflow_config": {
    "model": "stabilityai/stable-diffusion-xl-base-1.0",
    "scheduler": "DPMSolverMultistep",
    "steps": 50,
    "cfg_scale": 7.5,
    "pipeline": [
      {
        "node_type": "prompt_enhancement",
        "parameters": {
          "style_prompts": ["photorealistic", "high detail"]
        }
      },
      {
        "node_type": "generation",
        "parameters": {
          "negative_prompt": "cartoon, anime, low quality"
        }
      }
    ]
  }
}
```

## 📊 Monitoring

### Prometheus Metrics

The service exposes comprehensive metrics:
- HTTP request metrics (count, duration, status)
- Generation job metrics (count, duration, queue size)
- System health metrics (database, Redis, Celery)
- Custom business metrics (model usage, error rates)

### Health Checks

- **Liveness**: `/api/v1/health/live` - Service is running
- **Readiness**: `/api/v1/health/ready` - Service is ready to accept requests
- **Detailed**: `/api/v1/health/detailed` - Component-level health status

### Logging

Structured logging with:
- Request tracking with correlation IDs
- Component-specific loggers
- Error tracking and alerting
- Performance monitoring

## 🚀 Production Deployment

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with production configuration
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling Considerations

- **Horizontal Scaling**: Run multiple backend and worker instances
- **Database**: Use managed PostgreSQL service
- **Redis**: Use Redis Cluster for high availability
- **Storage**: Use production S3-compatible storage
- **Load Balancing**: Use nginx or cloud load balancer
- **CDN**: Serve generated images through CDN

### Security Checklist

- [ ] Change all default passwords and secrets
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure proper CORS origins
- [ ] Set up authentication and authorization
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor for security vulnerabilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow existing code style and conventions
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for workflow inspiration
- [Stable Diffusion](https://stability.ai/) for AI model architecture
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent Python framework
- [Next.js](https://nextjs.org/) for the React framework
- [shadcn/ui](https://ui.shadcn.com/) for beautiful UI components

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation and API reference
- Review existing issues and discussions

---

**Happy generating! 🎨✨**