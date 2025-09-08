#!/bin/bash
# =======================================================================================
# Docker Build Script for YouTube Blog Converter
# =======================================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="youtube-blog-converter"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
REGISTRY="${REGISTRY:-}"
PUSH_IMAGE="${PUSH_IMAGE:-false}"
RUN_TESTS="${RUN_TESTS:-true}"
TARGET="${TARGET:-production}"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --name NAME         Image name (default: youtube-blog-converter)"
    echo "  -v, --version VERSION   Image version (default: latest)"
    echo "  -r, --registry REGISTRY Docker registry (optional)"
    echo "  -t, --target TARGET     Build target (production, development, test-runner)"
    echo "  -p, --push             Push image to registry"
    echo "  --no-tests             Skip running tests during build"
    echo "  --no-cache             Build without cache"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --name myapp --version v1.0.0"
    echo "  $0 --registry myregistry.com --push"
    echo "  $0 --target development --no-tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -p|--push)
            PUSH_IMAGE="true"
            shift
            ;;
        --no-tests)
            RUN_TESTS="false"
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set full image name
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME"
else
    FULL_IMAGE_NAME="$IMAGE_NAME"
fi

# Validate target
case $TARGET in
    production|development|test-runner|unit-test|integration-test)
        ;;
    *)
        print_error "Invalid target: $TARGET"
        print_error "Valid targets: production, development, test-runner, unit-test, integration-test"
        exit 1
        ;;
esac

print_status "=== Docker Build Configuration ==="
print_status "Image Name: $FULL_IMAGE_NAME"
print_status "Version: $VERSION"
print_status "Target: $TARGET"
print_status "Build Date: $BUILD_DATE"
print_status "VCS Ref: $VCS_REF"
print_status "Run Tests: $RUN_TESTS"
print_status "Push Image: $PUSH_IMAGE"
echo ""

# Check if Dockerfile exists
if [[ ! -f "Dockerfile" ]]; then
    print_error "Dockerfile not found in current directory"
    exit 1
fi

# Check if .env.example exists
if [[ ! -f ".env.example" ]]; then
    print_warning ".env.example not found - creating template"
    cat > .env.example << 'EOF'
# YouTube Blog Converter Environment Variables
OPENAI_API_KEY=your_openai_api_key_here
SUPADATA_API_KEY=your_supadata_api_key_here
MONGODB_URI=mongodb://mongodb:27017/youtube_blog_db
MONGODB_DB_NAME=youtube_blog_db
JWT_SECRET_KEY=your_jwt_secret_key_here
FLASK_SECRET_KEY=your_flask_secret_key_here
LOG_LEVEL=INFO
EOF
fi

# Pre-build validation
print_status "Running pre-build validation..."

# Check for required files
REQUIRED_FILES=("requirements.txt" "run.py" "app")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -e "$file" ]]; then
        print_error "Required file/directory not found: $file"
        exit 1
    fi
done

print_success "Pre-build validation completed"

# Run tests before building production image
if [[ "$RUN_TESTS" == "true" && "$TARGET" == "production" ]]; then
    print_status "Running tests before production build..."
    
    # Build and run unit tests
    print_status "Building and running unit tests..."
    docker build --target unit-test \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VERSION="$VERSION" \
        --build-arg VCS_REF="$VCS_REF" \
        -t "$FULL_IMAGE_NAME:unit-test" \
        $NO_CACHE .
    
    print_success "Unit tests passed"
    
    # Build and run integration tests (may fail if no MongoDB available)
    print_status "Building and running integration tests..."
    docker build --target integration-test \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VERSION="$VERSION" \
        --build-arg VCS_REF="$VCS_REF" \
        -t "$FULL_IMAGE_NAME:integration-test" \
        $NO_CACHE . || print_warning "Integration tests failed - continuing with build"
    
    print_success "Test phase completed"
fi

# Build the main image
print_status "Building $TARGET image..."
docker build --target "$TARGET" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg VCS_REF="$VCS_REF" \
    -t "$FULL_IMAGE_NAME:$VERSION" \
    -t "$FULL_IMAGE_NAME:latest" \
    $NO_CACHE .

print_success "Successfully built $FULL_IMAGE_NAME:$VERSION"

# Show image details
print_status "Image details:"
docker images "$FULL_IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Security scan (if available)
if command -v docker scan &> /dev/null; then
    print_status "Running security scan..."
    docker scan "$FULL_IMAGE_NAME:$VERSION" --severity medium || print_warning "Security scan completed with warnings"
fi

# Push image if requested
if [[ "$PUSH_IMAGE" == "true" ]]; then
    if [[ -z "$REGISTRY" ]]; then
        print_error "Registry not specified but push requested"
        exit 1
    fi
    
    print_status "Pushing image to $REGISTRY..."
    docker push "$FULL_IMAGE_NAME:$VERSION"
    docker push "$FULL_IMAGE_NAME:latest"
    print_success "Successfully pushed image to registry"
fi

# Test run (optional)
if [[ "$TARGET" == "production" ]]; then
    print_status "Testing production image startup..."
    
    # Create a test network
    docker network create youtube-blog-test-net 2>/dev/null || true
    
    # Run a quick test
    CONTAINER_ID=$(docker run -d \
        --name youtube-blog-test \
        --network youtube-blog-test-net \
        -e OPENAI_API_KEY=test \
        -e SUPADATA_API_KEY=test \
        -e MONGODB_URI=mongodb://test:27017/test \
        -e FLASK_SECRET_KEY=test-secret-key-for-testing-super-secret-12345 \
        -e JWT_SECRET_KEY=test-jwt-secret \
        "$FULL_IMAGE_NAME:$VERSION")
    
    # Wait a moment for startup
    sleep 10
    
    # Check if container is still running
    if docker ps | grep -q "$CONTAINER_ID"; then
        print_success "Production image test successful"
    else
        print_warning "Production image may have startup issues"
        docker logs "$CONTAINER_ID"
    fi
    
    # Cleanup
    docker stop "$CONTAINER_ID" 2>/dev/null || true
    docker rm "$CONTAINER_ID" 2>/dev/null || true
    docker network rm youtube-blog-test-net 2>/dev/null || true
fi

print_success "Build process completed successfully!"

echo ""
print_status "=== Next Steps ==="
echo "To run the container:"
echo "  docker run -p 5000:5000 --env-file .env $FULL_IMAGE_NAME:$VERSION"
echo ""
echo "To run with docker-compose:"
echo "  docker-compose up app"
echo ""
echo "To run tests:"
echo "  docker run $FULL_IMAGE_NAME:unit-test"
echo "  docker-compose --profile test up test"