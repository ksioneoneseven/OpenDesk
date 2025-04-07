from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.assets import bp
from app.assets.forms import AssetForm, AssetFilterForm
from app.models import Asset, User, Ticket
from datetime import datetime, timedelta
from app.settings.routes import admin_required

@bp.route('/')
@login_required
def index():
    form = AssetFilterForm()
    
    # Get filter parameters
    asset_type = request.args.get('asset_type', '')
    status = request.args.get('status', '')
    assigned_to = request.args.get('assigned_to', type=int, default=0)
    
    # Base query
    query = Asset.query
    
    # Apply filters
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    if status:
        query = query.filter(Asset.status == status)
    
    if assigned_to > 0:
        query = query.filter(Asset.assigned_to_id == assigned_to)
    
    # Get assets
    assets = query.order_by(Asset.name).all()
    
    # Get counts for sidebar
    total_assets = Asset.query.count()
    in_use_assets = Asset.query.filter_by(status='in_use').count()
    available_assets = Asset.query.filter_by(status='available').count()
    maintenance_assets = Asset.query.filter_by(status='maintenance').count()
    
    # Get assets with expiring warranty (next 30 days)
    thirty_days_from_now = datetime.now().date() + timedelta(days=30)
    expiring_warranty = Asset.query.filter(
        Asset.warranty_expiry <= thirty_days_from_now,
        Asset.warranty_expiry >= datetime.now().date()
    ).count()
    
    return render_template('assets/index.html',
                          title='Assets',
                          assets=assets,
                          form=form,
                          total_assets=total_assets,
                          in_use_assets=in_use_assets,
                          available_assets=available_assets,
                          maintenance_assets=maintenance_assets,
                          expiring_warranty=expiring_warranty)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = AssetForm()
    
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            asset_type=form.asset_type.data,
            serial_number=form.serial_number.data,
            purchase_date=form.purchase_date.data,
            warranty_expiry=form.warranty_expiry.data,
            status=form.status.data,
            notes=form.notes.data
        )
        
        if form.assigned_to_id.data > 0:
            asset.assigned_to_id = form.assigned_to_id.data
        
        db.session.add(asset)
        db.session.commit()
        
        flash('Asset has been created successfully', 'success')
        return redirect(url_for('assets.view', id=asset.id))
    
    return render_template('assets/create.html', title='Create Asset', form=form)

@bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    asset = Asset.query.get_or_404(id)
    
    # Get related tickets
    tickets = asset.tickets.all()
    
    return render_template('assets/view.html',
                          title=f'Asset: {asset.name}',
                          asset=asset,
                          tickets=tickets)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    asset = Asset.query.get_or_404(id)
    form = AssetForm()
    
    if form.validate_on_submit():
        asset.name = form.name.data
        asset.asset_type = form.asset_type.data
        asset.serial_number = form.serial_number.data
        asset.purchase_date = form.purchase_date.data
        asset.warranty_expiry = form.warranty_expiry.data
        asset.status = form.status.data
        asset.notes = form.notes.data
        
        if form.assigned_to_id.data > 0:
            asset.assigned_to_id = form.assigned_to_id.data
        else:
            asset.assigned_to_id = None
        
        db.session.commit()
        
        flash('Asset has been updated successfully', 'success')
        return redirect(url_for('assets.view', id=asset.id))
    
    if request.method == 'GET':
        form.name.data = asset.name
        form.asset_type.data = asset.asset_type
        form.serial_number.data = asset.serial_number
        form.purchase_date.data = asset.purchase_date
        form.warranty_expiry.data = asset.warranty_expiry
        form.status.data = asset.status
        form.notes.data = asset.notes
        form.assigned_to_id.data = asset.assigned_to_id or 0
    
    return render_template('assets/edit.html', title='Edit Asset', form=form, asset=asset)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    asset = Asset.query.get_or_404(id)
    
    # Check if asset is associated with any tickets
    if asset.tickets.count() > 0:
        flash('Cannot delete asset that is associated with tickets', 'danger')
        return redirect(url_for('assets.view', id=asset.id))
    
    db.session.delete(asset)
    db.session.commit()
    
    flash('Asset has been deleted successfully', 'success')
    return redirect(url_for('assets.index'))

@bp.route('/<int:id>/assign', methods=['POST'])
@login_required
def assign(id):
    asset = Asset.query.get_or_404(id)
    user_id = request.form.get('user_id', type=int)
    
    if user_id == 0:
        asset.assigned_to_id = None
        asset.status = 'available'
        message = 'Asset unassigned successfully'
    else:
        user = User.query.get_or_404(user_id)
        asset.assigned_to_id = user.id
        asset.status = 'in_use'
        message = f'Asset assigned to {user.full_name} successfully'
    
    db.session.commit()
    
    flash(message, 'success')
    return redirect(url_for('assets.view', id=asset.id))
