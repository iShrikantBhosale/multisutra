# MultiSutra CMS

A powerful multi-tenant content management system built with Flask, designed for creating and managing multiple independent blogs from a single codebase.

## Features

### 🏢 Multi-Tenant Architecture
- **Subdomain-based tenancy**: Each blog runs on its own subdomain (e.g., `blog1.multisutra.com`)
- **Isolated data**: Complete separation of content, users, and settings per tenant
- **Shared codebase**: Single deployment manages unlimited blogs
- **Custom domains**: Support for custom domain mapping

### ✍️ Content Management
- **Rich text editor**: WYSIWYG editor with TinyMCE integration
- **Media library**: Upload and manage images, videos, and documents
- **Categories & Tags**: Organize content with hierarchical categories and tags
- **Featured posts**: Highlight important content
- **Draft system**: Save and preview posts before publishing
- **Scheduled publishing**: Set posts to publish at future dates

### 👥 User Management
- **Role-based access**: Admin and Editor roles per tenant
- **User profiles**: Customizable user profiles with avatars
- **Authentication**: Secure login system with password reset
- **Multi-tenant users**: Users are isolated per tenant

### 🎨 Theming & Customization
- **Template system**: Dynamic template loading with placeholders
- **Custom CSS/JS**: Per-tenant custom styling and scripts
- **Responsive design**: Mobile-first Bootstrap-based themes
- **Ad spaces**: Built-in ad placement areas
- **Social media integration**: Social media links and sharing

### 🔍 SEO & Analytics
- **Meta tags**: Automatic and custom meta tag generation
- **XML sitemaps**: Auto-generated sitemaps per tenant
- **Schema markup**: Structured data for better search results
- **Google Analytics**: Per-tenant analytics integration
- **RSS feeds**: Auto-generated RSS feeds
- **Social sharing**: Open Graph and Twitter Card support

### ⚡ Performance
- **Caching**: Redis-based caching system
- **Image optimization**: Automatic image compression and thumbnails
- **CDN ready**: Easy integration with CDNs
- **Database optimization**: Efficient queries with proper indexing

### 🔒 Security
- **Rate limiting**: Protection against abuse
- **CSRF protection**: Built-in CSRF tokens
- **Content sanitization**: HTML sanitization for user content
- **Secure uploads**: File type validation and secure storage

## Tech Stack

- **Backend**: Flask (Python 3.11+)
- **Database**: PostgreSQL (SQLite for development)
- **Cache**: Redis
- **Frontend**: Bootstrap 5, Font Awesome
- **Editor**: TinyMCE/Quill.js
- **Authentication**: Flask-Login
- **File Uploads**: Local storage with S3 support
- **Deployment**: Docker, Docker Compose, Render

## Quick Start

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd multisutra
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize database**:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. **Create a super admin**:
   ```bash
   python app.py create-super-admin
   ```

6. **Run the application**:
   ```bash
   python app.py
   ```

7. **Access the application**:
   - Main site: `http://localhost:5000`
   - Admin panel: `http://admin.localhost:5000/admin` (requires super admin)
   - Sample blog: `http://demo.localhost:5000`

### Docker Development

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Initialize database**:
   ```bash
   docker-compose exec web flask db upgrade
   docker-compose exec web python app.py create-super-admin
   ```

## Production Deployment

### Deploy to Render

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on Render:
   - Connect your GitHub repository
   - Use the following settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`

3. **Add environment variables**:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key
   DATABASE_URL=your-postgres-url
   REDIS_URL=your-redis-url
   MAIN_DOMAIN=your-domain.com
   ```

4. **Set up database**:
   - Create a PostgreSQL database on Render
   - Run migrations in the Render console:
     ```bash
     flask db upgrade
     python app.py create-super-admin
     ```

### Deploy with Docker

1. **Build and push to registry**:
   ```bash
   docker build -t your-registry/multisutra-cms .
   docker push your-registry/multisutra-cms
   ```

2. **Deploy to your server**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Custom Domain Setup

1. **Configure DNS**:
   - Add A record: `*.yourdomain.com` → Your server IP
   - Add CNAME: `www.yourdomain.com` → `yourdomain.com`

2. **Update environment**:
   ```bash
   MAIN_DOMAIN=yourdomain.com
   ALLOWED_SUBDOMAINS=blog1,blog2,demo
   ```

3. **SSL Certificate** (with Let's Encrypt):
   ```bash
   certbot --nginx -d yourdomain.com -d *.yourdomain.com
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | development |
| `SECRET_KEY` | Flask secret key | auto-generated |
| `DATABASE_URL` | Database connection string | SQLite |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `MAIN_DOMAIN` | Primary domain | multisutra.com |
| `ALLOWED_SUBDOMAINS` | Comma-separated list of allowed subdomains | - |
| `UPLOAD_FOLDER` | File upload directory | static/uploads |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | 16MB |
| `GOOGLE_ANALYTICS_ID` | Global GA tracking ID | - |
| `SENTRY_DSN` | Sentry error tracking DSN | - |

### Super Admin Setup

Super admins can access the `/admin` panel to manage all tenants. Set the `SUPER_ADMINS` environment variable with comma-separated email addresses:

```bash
SUPER_ADMINS=admin@example.com,superuser@example.com
```

## Usage Guide

### Creating a New Blog

1. **Access the main domain** (e.g., `multisutra.com`)
2. **Enter a subdomain** in the form (e.g., "myblog")
3. **Visit the subdomain** (e.g., `myblog.multisutra.com`)
4. **Register as the first user** (becomes admin automatically)
5. **Start creating content** in the dashboard

### Managing Content

1. **Login** to your blog subdomain
2. **Access the dashboard** via the user menu
3. **Create posts** using the rich text editor
4. **Upload media** to the media library
5. **Organize with categories and tags**
6. **Configure blog settings** (admin only)

### Customization

1. **Themes**: Upload custom CSS in tenant settings
2. **Logo**: Upload logo image in tenant settings
3. **Social media**: Configure social media links
4. **SEO**: Set meta descriptions and keywords
5. **Analytics**: Add Google Analytics tracking ID

## API Documentation

### REST API Endpoints

- `GET /api/posts` - List posts
- `GET /api/posts/{id}` - Get single post
- `GET /api/categories` - List categories
- `GET /api/tags` - List tags
- `GET /api/media` - List media files
- `GET /api/search` - Search content

### Authentication

API endpoints require authentication via session cookies. Use the web interface to authenticate, then make API calls from the same browser session.

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes and test thoroughly**
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 for Python code style
- Use type hints where appropriate
- Add docstrings for functions and classes
- Write tests for new features
- Update documentation for changes

## Troubleshooting

### Common Issues

**Subdomain not working locally**:
- Add entries to `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):
  ```
  127.0.0.1 demo.localhost
  127.0.0.1 admin.localhost
  ```

**Database connection error**:
- Check DATABASE_URL environment variable
- Ensure PostgreSQL/SQLite is running
- Run `flask db upgrade` to create tables

**File upload fails**:
- Check UPLOAD_FOLDER permissions
- Verify MAX_CONTENT_LENGTH setting
- Ensure disk space available

**CSS/JS not loading**:
- Check static file configuration
- Clear browser cache
- Verify CDN settings in production

### Getting Help

- **Documentation**: Check this README and inline code comments
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Flask** - The web framework that powers this CMS
- **Bootstrap** - For the responsive UI components
- **TinyMCE** - Rich text editing capabilities
- **Font Awesome** - Icons throughout the interface
- **Contributors** - Everyone who has contributed to this project

---

Built with ❤️ for the blogging community