"""
Media Module - Handles file uploads, media management, and asset handling
Modular design inspired by Astro's approach
"""

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from PIL import Image
import mimetypes

from app import db
from app.models import MediaFile

class MediaModule:
    """Media module for file upload and management"""
    
    def __init__(self):
        self.blueprint = Blueprint('media', __name__)
        self.allowed_extensions = {
            'images': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'},
            'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
            'archives': {'zip', 'rar', '7z', 'tar', 'gz'}
        }
        self._register_routes()
    
    def _register_routes(self):
        """Register all media routes"""
        self.blueprint.add_url_rule('/upload', 'upload', self.upload, methods=['POST'])
        self.blueprint.add_url_rule('/library', 'library', self.library)
        self.blueprint.add_url_rule('/search', 'search', self.search)
        self.blueprint.add_url_rule('/<int:id>', 'get_media', self.get_media)
        self.blueprint.add_url_rule('/<int:id>/delete', 'delete_media', self.delete_media, methods=['DELETE'])
        self.blueprint.add_url_rule('/<int:id>/update', 'update_media', self.update_media, methods=['PUT'])
    
    @login_required
    def upload(self):
        """Handle file upload"""
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': 'No files provided'})
        
        files = request.files.getlist('files')
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            result = self._process_upload(file)
            if result['success']:
                uploaded_files.append(result['media_file'])
            else:
                errors.append(f"{file.filename}: {result['message']}")
        
        return jsonify({
            'success': len(uploaded_files) > 0,
            'uploaded': len(uploaded_files),
            'errors': errors,
            'files': [self._serialize_media_file(f) for f in uploaded_files]
        })
    
    @login_required
    def library(self):
        """Get media library"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        file_type = request.args.get('type', 'all')
        
        query = MediaFile.query
        
        if file_type != 'all':
            if file_type == 'images':
                query = query.filter(MediaFile.mime_type.startswith('image/'))
            elif file_type == 'documents':
                query = query.filter(MediaFile.mime_type.startswith('application/'))
        
        media_files = query.order_by(MediaFile.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'files': [self._serialize_media_file(f) for f in media_files.items],
            'pagination': {
                'page': media_files.page,
                'pages': media_files.pages,
                'per_page': media_files.per_page,
                'total': media_files.total,
                'has_next': media_files.has_next,
                'has_prev': media_files.has_prev
            }
        })
    
    @login_required
    def search(self):
        """Search media files"""
        query = request.args.get('q', '').strip()
        file_type = request.args.get('type', 'all')
        
        if not query:
            return jsonify({'success': False, 'message': 'Search query required'})
        
        media_query = MediaFile.query.filter(
            MediaFile.original_filename.contains(query) |
            MediaFile.alt_text.contains(query) |
            MediaFile.description.contains(query)
        )
        
        if file_type != 'all':
            if file_type == 'images':
                media_query = media_query.filter(MediaFile.mime_type.startswith('image/'))
            elif file_type == 'documents':
                media_query = media_query.filter(MediaFile.mime_type.startswith('application/'))
        
        results = media_query.order_by(MediaFile.created_at.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'files': [self._serialize_media_file(f) for f in results]
        })
    
    @login_required
    def get_media(self, id):
        """Get single media file"""
        media_file = MediaFile.query.get_or_404(id)
        return jsonify({
            'success': True,
            'file': self._serialize_media_file(media_file)
        })
    
    @login_required
    def delete_media(self, id):
        """Delete media file"""
        media_file = MediaFile.query.get_or_404(id)
        
        try:
            # Delete physical file
            if os.path.exists(media_file.file_path):
                os.remove(media_file.file_path)
            
            # Delete thumbnails if they exist
            self._delete_thumbnails(media_file)
            
            db.session.delete(media_file)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'File deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500
    
    @login_required
    def update_media(self, id):
        """Update media file metadata"""
        media_file = MediaFile.query.get_or_404(id)
        
        try:
            data = request.get_json()
            
            if 'alt_text' in data:
                media_file.alt_text = data['alt_text']
            if 'description' in data:
                media_file.description = data['description']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'file': self._serialize_media_file(media_file)
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error updating file: {str(e)}'}), 500
    
    def _process_upload(self, file):
        """Process single file upload"""
        try:
            # Validate file
            validation_result = self._validate_file(file)
            if not validation_result['valid']:
                return {'success': False, 'message': validation_result['message']}
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = self._get_file_extension(original_filename)
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Determine upload directory
            upload_dir = self._get_upload_directory()
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or file.content_type
            
            # Process image if applicable
            width, height = None, None
            if mime_type and mime_type.startswith('image/'):
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        # Create thumbnail
                        self._create_thumbnail(file_path, unique_filename)
                except Exception:
                    pass  # Not a valid image or PIL not available
            
            # Create database record
            media_file = MediaFile(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                uploaded_by_id=current_user.id
            )
            
            db.session.add(media_file)
            db.session.commit()
            
            return {'success': True, 'media_file': media_file}
            
        except Exception as e:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            return {'success': False, 'message': f'Upload failed: {str(e)}'}
    
    def _validate_file(self, file):
        """Validate uploaded file"""
        if not file or not file.filename:
            return {'valid': False, 'message': 'No file provided'}
        
        # Check file extension
        file_extension = self._get_file_extension(file.filename).lower()
        all_allowed = set()
        for extensions in self.allowed_extensions.values():
            all_allowed.update(extensions)
        
        if file_extension not in all_allowed:
            return {'valid': False, 'message': f'File type .{file_extension} not allowed'}
        
        # Check file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Reset to beginning
        
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return {'valid': False, 'message': 'File size exceeds 10MB limit'}
        
        return {'valid': True}
    
    def _get_file_extension(self, filename):
        """Get file extension"""
        return filename.rsplit('.', 1)[1] if '.' in filename else ''
    
    def _get_upload_directory(self):
        """Get upload directory path"""
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        today = datetime.now()
        return os.path.join(upload_dir, str(today.year), f"{today.month:02d}")
    
    def _create_thumbnail(self, file_path, filename):
        """Create thumbnail for image"""
        try:
            thumbnail_dir = os.path.join(os.path.dirname(file_path), 'thumbnails')
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            thumbnail_path = os.path.join(thumbnail_dir, f"thumb_{filename}")
            
            with Image.open(file_path) as img:
                # Create thumbnail (300x300 max, maintain aspect ratio)
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(thumbnail_path, optimize=True)
                
        except Exception:
            pass  # Thumbnail creation failed, but that's okay
    
    def _delete_thumbnails(self, media_file):
        """Delete associated thumbnails"""
        try:
            thumbnail_dir = os.path.join(os.path.dirname(media_file.file_path), 'thumbnails')
            thumbnail_path = os.path.join(thumbnail_dir, f"thumb_{media_file.filename}")
            
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                
        except Exception:
            pass  # Thumbnail deletion failed, but that's okay
    
    def _serialize_media_file(self, media_file):
        """Convert media file to JSON-serializable dict"""
        return {
            'id': media_file.id,
            'filename': media_file.filename,
            'original_filename': media_file.original_filename,
            'file_size': media_file.file_size,
            'mime_type': media_file.mime_type,
            'width': media_file.width,
            'height': media_file.height,
            'alt_text': media_file.alt_text,
            'description': media_file.description,
            'is_image': media_file.is_image,
            'url': url_for('static', filename=f'uploads/{media_file.filename}'),
            'thumbnail_url': url_for('static', filename=f'uploads/thumbnails/thumb_{media_file.filename}') if media_file.is_image else None,
            'uploaded_by': media_file.uploaded_by.username if media_file.uploaded_by else None,
            'created_at': media_file.created_at.isoformat()
        }
    
    def get_media_stats(self):
        """Get media statistics"""
        return {
            'total_files': MediaFile.query.count(),
            'total_images': MediaFile.query.filter(MediaFile.mime_type.startswith('image/')).count(),
            'total_size': db.session.query(db.func.sum(MediaFile.file_size)).scalar() or 0
        }

# Create module instance
media_module = MediaModule()