import os
import uuid
import shutil
import markdown
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.knowledge_base import bp
from app.models import KnowledgeBaseArticle, KnowledgeBaseCategory, KnowledgeBaseImage
from app.knowledge_base.forms import ArticleForm, CategoryForm, KnowledgeBaseSearchForm

@bp.route('/')
@login_required
def index():
    # Get all published articles
    articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.created_at.desc()).all()
    categories = KnowledgeBaseCategory.query.all()
    
    # Get recent articles (last 5)
    recent_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.created_at.desc()).limit(5).all()
    
    # Get popular articles (most viewed, up to 5)
    popular_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.view_count.desc()).limit(5).all()
    
    return render_template('knowledge_base/index.html', 
                          title='Knowledge Base',
                          articles=articles,
                          categories=categories,
                          recent_articles=recent_articles,
                          popular_articles=popular_articles)

@bp.route('/category/<int:id>')
@login_required
def view_category(id):
    category = KnowledgeBaseCategory.query.get_or_404(id)
    articles = KnowledgeBaseArticle.query.filter_by(category_id=id, is_published=True).all()
    return render_template('knowledge_base/category.html',
                          title=f'Category: {category.name}',
                          category=category,
                          articles=articles)

@bp.route('/article/<int:id>')
@login_required
def view_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    categories = KnowledgeBaseCategory.query.all()
    
    # Get related articles (same category, excluding current article)
    related_articles = KnowledgeBaseArticle.query.filter(
        KnowledgeBaseArticle.category_id == article.category_id,
        KnowledgeBaseArticle.id != article.id,
        KnowledgeBaseArticle.is_published == True
    ).limit(5).all()
    
    # Increment view count
    article.view_count += 1
    db.session.commit()
    
    # Render markdown content if needed
    content_html = None
    if article.file_format == 'md':
        content_html = markdown.markdown(article.content)
    
    # Get images for this article
    images = KnowledgeBaseImage.query.filter_by(article_id=article.id).all()
    
    return render_template('knowledge_base/article.html',
                          title=article.title,
                          article=article,
                          categories=categories,
                          related_articles=related_articles,
                          content_html=content_html,
                          images=images)

@bp.route('/articles/<int:id>/delete', methods=['POST'])
@login_required
def delete_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    
    # Check if user is admin or the creator of the article
    if current_user.is_administrator() or article.created_by == current_user.id:
        # Delete associated images first
        for image in article.images:
            try:
                # Delete the file from the filesystem
                image_path = os.path.join(upload_folder, image.filename)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                flash(f'Error deleting image file: {str(e)}', 'danger')
            
        # Delete the article from the database
        db.session.delete(article)
        db.session.commit()
        
        flash('Article has been deleted successfully', 'success')
    else:
        flash('You do not have permission to delete this article', 'danger')
        
    return redirect(url_for('kb.index'))



@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = KnowledgeBaseSearchForm()
    results = []
    
    if form.validate_on_submit() or request.args.get('query'):
        query = form.query.data or request.args.get('query')
        category_id = form.category_id.data or request.args.get('category_id', 0, type=int)
        
        if category_id > 0:
            results = KnowledgeBaseArticle.query.filter(
                KnowledgeBaseArticle.is_published == True,
                KnowledgeBaseArticle.category_id == category_id,
                (KnowledgeBaseArticle.title.contains(query) | KnowledgeBaseArticle.content.contains(query))
            ).all()
        else:
            results = KnowledgeBaseArticle.query.filter(
                KnowledgeBaseArticle.is_published == True,
                (KnowledgeBaseArticle.title.contains(query) | KnowledgeBaseArticle.content.contains(query))
            ).all()
    
    return render_template('knowledge_base/search.html',
                          title='Search Knowledge Base',
                          form=form,
                          results=results)

@bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = KnowledgeBaseCategory(
            name=form.name.data,
            description=form.description.data,
            parent_id=form.parent_id.data or None,
            is_private=form.is_private.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category has been created successfully', 'success')
        return redirect(url_for('kb.index'))
    
    return render_template('knowledge_base/create_category.html',
                          title='Create Category',
                          form=form)

@bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = KnowledgeBaseCategory.query.get_or_404(id)
    form = CategoryForm()
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.parent_id = form.parent_id.data or None
        category.is_private = form.is_private.data
        
        db.session.commit()
        
        flash('Category has been updated successfully', 'success')
        return redirect(url_for('kb.view_category', id=category.id))
    elif request.method == 'GET':
        form.name.data = category.name
        form.description.data = category.description
        form.parent_id.data = category.parent_id if category.parent_id else 0
        form.is_private.data = category.is_private
    
    return render_template('knowledge_base/edit_category.html',
                          title='Edit Category',
                          form=form,
                          category=category)

@bp.route('/articles/create', methods=['GET', 'POST'])
@login_required
def create_article():
    form = ArticleForm()
    form.category_id.choices = [(c.id, c.name) for c in KnowledgeBaseCategory.query.all()]
    
    if form.validate_on_submit():
        # Create article
        article = KnowledgeBaseArticle(
            title=form.title.data,
            content=form.content.data,
            category_id=form.category_id.data,
            is_published=form.is_published.data,
            file_format=form.file_format.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        
        db.session.add(article)
        db.session.flush()  # Get the article ID
        
        # Handle image uploads
        if form.images.data and any(form.images.data):
            # Create a test images directory first (this worked in the test tool)
            test_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'test_images')
            os.makedirs(test_upload_dir, exist_ok=True)
            
            # Then create the KB images directory
            kb_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'kb_images', str(article.id))
            os.makedirs(kb_upload_dir, exist_ok=True)
            
            # Process each uploaded image
            for image_file in request.files.getlist('images'):
                if image_file and image_file.filename.strip():
                    # Generate a secure filename with UUID to prevent collisions
                    filename = secure_filename(image_file.filename)
                    unique_filename = f"article_{uuid.uuid4().hex}_{filename}"
                    
                    # First save to test directory (this worked in the test tool)
                    test_file_path = os.path.join(test_upload_dir, unique_filename)
                    image_file.save(test_file_path)
                    
                    # Then copy to KB directory
                    kb_file_path = os.path.join(kb_upload_dir, unique_filename)
                    shutil.copy2(test_file_path, kb_file_path)
                    
                    # Create image record in database
                    image = KnowledgeBaseImage(
                        filename=unique_filename,
                        file_path=os.path.join('kb_images', str(article.id), unique_filename),
                        article_id=article.id,
                        uploaded_by=current_user.id
                    )
                    db.session.add(image)
        
        db.session.commit()
        
        flash('Article has been created successfully', 'success')
        return redirect(url_for('kb.view_article', id=article.id))
    
    return render_template('knowledge_base/create_article.html',
                          title='Create Article',
                          form=form)

@bp.route('/articles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    form = ArticleForm()
    form.category_id.choices = [(c.id, c.name) for c in KnowledgeBaseCategory.query.all()]
    
    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data
        article.category_id = form.category_id.data
        article.is_published = form.is_published.data
        article.file_format = form.file_format.data
        article.updated_by = current_user.id
        
        # Handle image uploads
        if form.images.data and any(form.images.data):
            # Create a test images directory first (this worked in the test tool)
            test_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'test_images')
            os.makedirs(test_upload_dir, exist_ok=True)
            
            # Then create the KB images directory
            kb_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'kb_images', str(article.id))
            os.makedirs(kb_upload_dir, exist_ok=True)
            
            # Process each uploaded image
            for image_file in request.files.getlist('images'):
                if image_file and image_file.filename.strip():
                    # Generate a secure filename with UUID to prevent collisions
                    filename = secure_filename(image_file.filename)
                    unique_filename = f"article_{uuid.uuid4().hex}_{filename}"
                    
                    # First save to test directory (this worked in the test tool)
                    test_file_path = os.path.join(test_upload_dir, unique_filename)
                    image_file.save(test_file_path)
                    
                    # Then copy to KB directory
                    kb_file_path = os.path.join(kb_upload_dir, unique_filename)
                    shutil.copy2(test_file_path, kb_file_path)
                    
                    # Create image record in database
                    image = KnowledgeBaseImage(
                        filename=unique_filename,
                        file_path=os.path.join('kb_images', str(article.id), unique_filename),
                        article_id=article.id,
                        uploaded_by=current_user.id
                    )
                    db.session.add(image)
        
        db.session.commit()
        
        flash('Article has been updated successfully', 'success')
        return redirect(url_for('kb.view_article', id=article.id))
    elif request.method == 'GET':
        form.title.data = article.title
        form.content.data = article.content
        form.category_id.data = article.category_id
        form.is_published.data = article.is_published
        form.file_format.data = article.file_format
    
    return render_template('knowledge_base/edit_article.html',
                          title='Edit Article',
                          form=form,
                          article=article)

# Add this function to serve images correctly
@bp.route('/images/<path:filename>')
def serve_kb_image(filename):
    # The images are stored in the static/uploads directory
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)
