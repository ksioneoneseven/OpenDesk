from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.knowledge_base import bp
from app.knowledge_base.forms import CategoryForm, ArticleForm, KnowledgeBaseSearchForm
from app.models import KnowledgeBaseCategory, KnowledgeBaseArticle
from app.settings.routes import admin_required
from sqlalchemy import or_
from datetime import datetime

@bp.route('/')
@login_required
def index():
    # Get all top-level categories
    categories = KnowledgeBaseCategory.query.filter_by(parent_id=None).all()
    
    # Get recent articles
    recent_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.updated_at.desc()).limit(5).all()
    
    # Get most viewed articles
    popular_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.view_count.desc()).limit(5).all()
    
    # Search form
    search_form = KnowledgeBaseSearchForm()
    
    return render_template('knowledge_base/index.html',
                          title='Knowledge Base',
                          categories=categories,
                          recent_articles=recent_articles,
                          popular_articles=popular_articles,
                          search_form=search_form)

@bp.route('/search')
@login_required
def search():
    query = request.args.get('query', '')
    category_id = request.args.get('category_id', type=int, default=0)
    
    if not query:
        return redirect(url_for('knowledge_base.index'))
    
    # Base query
    article_query = KnowledgeBaseArticle.query.filter_by(is_published=True)
    
    # Apply category filter if specified
    if category_id > 0:
        article_query = article_query.filter_by(category_id=category_id)
    
    # Apply search query
    search_terms = query.split()
    search_filter = []
    for term in search_terms:
        search_filter.append(KnowledgeBaseArticle.title.ilike(f'%{term}%'))
        search_filter.append(KnowledgeBaseArticle.content.ilike(f'%{term}%'))
    
    article_query = article_query.filter(or_(*search_filter))
    
    # Get results
    articles = article_query.order_by(KnowledgeBaseArticle.title).all()
    
    # Search form for the results page
    search_form = KnowledgeBaseSearchForm()
    search_form.query.data = query
    search_form.category_id.data = category_id
    
    return render_template('knowledge_base/search_results.html',
                          title='Search Results',
                          articles=articles,
                          search_form=search_form,
                          query=query)

@bp.route('/categories')
@login_required
@admin_required
def categories():
    categories = KnowledgeBaseCategory.query.order_by(KnowledgeBaseCategory.name).all()
    return render_template('knowledge_base/categories.html',
                          title='Knowledge Base Categories',
                          categories=categories)

@bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    form = CategoryForm()
    
    # Remove the current category from parent options to prevent circular references
    if request.method == 'GET':
        form.parent_id.choices = [(0, 'None (Top Level)')] + [
            (c.id, c.name) for c in KnowledgeBaseCategory.query.order_by(KnowledgeBaseCategory.name).all()
        ]
    
    if form.validate_on_submit():
        category = KnowledgeBaseCategory(
            name=form.name.data,
            description=form.description.data
        )
        
        if form.parent_id.data > 0:
            category.parent_id = form.parent_id.data
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category has been created successfully', 'success')
        return redirect(url_for('knowledge_base.categories'))
    
    return render_template('knowledge_base/create_category.html',
                          title='Create Category',
                          form=form)

@bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(id):
    category = KnowledgeBaseCategory.query.get_or_404(id)
    form = CategoryForm()
    
    # Remove the current category from parent options to prevent circular references
    if request.method == 'GET':
        form.parent_id.choices = [(0, 'None (Top Level)')] + [
            (c.id, c.name) for c in KnowledgeBaseCategory.query.filter(KnowledgeBaseCategory.id != id).order_by(KnowledgeBaseCategory.name).all()
        ]
        form.name.data = category.name
        form.description.data = category.description
        form.parent_id.data = category.parent_id or 0
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        if form.parent_id.data > 0:
            # Check if the selected parent is not a descendant of this category
            parent = KnowledgeBaseCategory.query.get(form.parent_id.data)
            current_parent = parent
            while current_parent:
                if current_parent.id == category.id:
                    flash('Cannot set a descendant as the parent category', 'danger')
                    return redirect(url_for('knowledge_base.edit_category', id=id))
                current_parent = current_parent.parent
            
            category.parent_id = form.parent_id.data
        else:
            category.parent_id = None
        
        db.session.commit()
        
        flash('Category has been updated successfully', 'success')
        return redirect(url_for('knowledge_base.categories'))
    
    return render_template('knowledge_base/edit_category.html',
                          title='Edit Category',
                          form=form,
                          category=category)

@bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    category = KnowledgeBaseCategory.query.get_or_404(id)
    
    # Check if category has articles
    if category.articles.count() > 0:
        flash('Cannot delete category that contains articles', 'danger')
        return redirect(url_for('knowledge_base.categories'))
    
    # Check if category has subcategories
    if category.children.count() > 0:
        flash('Cannot delete category that contains subcategories', 'danger')
        return redirect(url_for('knowledge_base.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category has been deleted successfully', 'success')
    return redirect(url_for('knowledge_base.categories'))

@bp.route('/category/<int:id>')
@login_required
def view_category(id):
    category = KnowledgeBaseCategory.query.get_or_404(id)
    
    # Get subcategories
    subcategories = category.children.all()
    
    # Get articles in this category
    articles = category.articles.filter_by(is_published=True).order_by(KnowledgeBaseArticle.title).all()
    
    # Search form
    search_form = KnowledgeBaseSearchForm()
    
    return render_template('knowledge_base/view_category.html',
                          title=f'Category: {category.name}',
                          category=category,
                          subcategories=subcategories,
                          articles=articles,
                          search_form=search_form)

@bp.route('/articles')
@login_required
@admin_required
def articles():
    articles = KnowledgeBaseArticle.query.order_by(KnowledgeBaseArticle.title).all()
    return render_template('knowledge_base/articles.html',
                          title='Knowledge Base Articles',
                          articles=articles)

@bp.route('/articles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_article():
    form = ArticleForm()
    
    # Check if there are any categories
    if KnowledgeBaseCategory.query.count() == 0:
        flash('You need to create at least one category before creating articles', 'warning')
        return redirect(url_for('knowledge_base.create_category'))
    
    if form.validate_on_submit():
        article = KnowledgeBaseArticle(
            title=form.title.data,
            content=form.content.data,
            category_id=form.category_id.data,
            is_published=form.is_published.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        
        db.session.add(article)
        db.session.commit()
        
        flash('Article has been created successfully', 'success')
        return redirect(url_for('knowledge_base.view_article', id=article.id))
    
    return render_template('knowledge_base/create_article.html',
                          title='Create Article',
                          form=form)

@bp.route('/articles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    form = ArticleForm()
    
    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data
        article.category_id = form.category_id.data
        article.is_published = form.is_published.data
        article.updated_by = current_user.id
        article.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Article has been updated successfully', 'success')
        return redirect(url_for('knowledge_base.view_article', id=article.id))
    
    if request.method == 'GET':
        form.title.data = article.title
        form.content.data = article.content
        form.category_id.data = article.category_id
        form.is_published.data = article.is_published
    
    return render_template('knowledge_base/edit_article.html',
                          title='Edit Article',
                          form=form,
                          article=article)

@bp.route('/articles/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    
    db.session.delete(article)
    db.session.commit()
    
    flash('Article has been deleted successfully', 'success')
    return redirect(url_for('knowledge_base.articles'))

@bp.route('/articles/<int:id>')
@login_required
def view_article(id):
    article = KnowledgeBaseArticle.query.get_or_404(id)
    
    # Increment view count
    article.view_count += 1
    db.session.commit()
    
    # Get related articles in the same category
    related_articles = KnowledgeBaseArticle.query.filter(
        KnowledgeBaseArticle.category_id == article.category_id,
        KnowledgeBaseArticle.id != article.id,
        KnowledgeBaseArticle.is_published == True
    ).order_by(KnowledgeBaseArticle.view_count.desc()).limit(5).all()
    
    # Search form
    search_form = KnowledgeBaseSearchForm()
    
    return render_template('knowledge_base/view_article.html',
                          title=article.title,
                          article=article,
                          related_articles=related_articles,
                          search_form=search_form)
