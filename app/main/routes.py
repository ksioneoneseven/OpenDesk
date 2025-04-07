from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Ticket, TicketStatus, TicketPriority, User, TimeEntry, Asset, KnowledgeBaseArticle
from sqlalchemy import func, and_
from datetime import datetime, timedelta

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get ticket counts by status
    statuses = TicketStatus.query.all()
    status_counts = {}
    for status in statuses:
        count = Ticket.query.filter_by(status_id=status.id).count()
        status_counts[status.name] = {
            'count': count,
            'color': status.color
        }
    
    # Get ticket counts by priority
    priorities = TicketPriority.query.all()
    priority_counts = {}
    for priority in priorities:
        count = Ticket.query.filter_by(priority_id=priority.id).count()
        priority_counts[priority.name] = {
            'count': count,
            'color': priority.color
        }
    
    # Get open tickets assigned to current user
    my_tickets = Ticket.query.join(TicketStatus).filter(
        Ticket.assigned_to == current_user.id,
        TicketStatus.is_closed == False
    ).order_by(Ticket.created_at.desc()).limit(5).all()
    
    # Get recent tickets
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()
    
    # Get overdue tickets
    overdue_tickets = Ticket.query.filter(
        Ticket.due_date < datetime.utcnow(),
        Ticket.status.has(TicketStatus.is_closed == False)
    ).count()
    
    # Get SLA breached tickets
    sla_breached = Ticket.query.filter(
        and_(
            Ticket.status.has(TicketStatus.is_closed == False),
            (
                and_(Ticket.sla_response_due < datetime.utcnow(), Ticket.sla_response_met == False) |
                and_(Ticket.sla_resolution_due < datetime.utcnow(), Ticket.sla_resolution_met == False)
            )
        )
    ).count()
    
    # Get SLA at risk tickets (within 75% of SLA time)
    now = datetime.utcnow()
    at_risk_tickets = Ticket.query.filter(
        and_(
            Ticket.status.has(TicketStatus.is_closed == False),
            (
                and_(
                    Ticket.sla_response_met == False,
                    Ticket.sla_response_due > now,
                    Ticket.sla_response_due < now + timedelta(hours=4)
                ) |
                and_(
                    Ticket.sla_resolution_met == False,
                    Ticket.sla_resolution_due > now,
                    Ticket.sla_resolution_due < now + timedelta(hours=8)
                )
            )
        )
    ).count()
    
    # Get ticket volume over time (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_tickets = db.session.query(
        func.date(Ticket.created_at).label('date'),
        func.count(Ticket.id).label('count')
    ).filter(Ticket.created_at >= seven_days_ago).group_by(func.date(Ticket.created_at)).all()
    
    daily_ticket_data = {
        'labels': [str(day.date) for day in daily_tickets],
        'counts': [day.count for day in daily_tickets]
    }
    
    # Get agent performance metrics
    agents = User.query.join(User.role).filter(User.role.has(name='Agent')).all()
    agent_metrics = []
    
    for agent in agents:
        closed_tickets = Ticket.query.filter(
            Ticket.assigned_to == agent.id,
            Ticket.status.has(TicketStatus.is_closed == True)
        ).count()
        
        total_time = db.session.query(func.sum(TimeEntry.duration)).filter(
            TimeEntry.user_id == agent.id
        ).scalar() or 0
        
        agent_metrics.append({
            'name': agent.full_name,
            'closed_tickets': closed_tickets,
            'total_time': total_time
        })
    
    # Get asset statistics
    total_assets = Asset.query.count()
    assigned_assets = Asset.query.filter(Asset.assigned_to_id != None).count()
    
    # Get knowledge base statistics
    kb_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).count()
    
    return render_template('main/dashboard.html', 
                           title='Dashboard',
                           status_counts=status_counts,
                           priority_counts=priority_counts,
                           my_tickets=my_tickets,
                           recent_tickets=recent_tickets,
                           overdue_tickets=overdue_tickets,
                           sla_breached=sla_breached,
                           at_risk_tickets=at_risk_tickets,
                           daily_ticket_data=daily_ticket_data,
                           agent_metrics=agent_metrics,
                           total_assets=total_assets,
                           assigned_assets=assigned_assets,
                           kb_articles=kb_articles)

@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.dashboard'))
    
    # Search tickets
    tickets = Ticket.query.filter(
        (Ticket.subject.contains(query)) |
        (Ticket.description.contains(query)) |
        (Ticket.requester_email.contains(query)) |
        (Ticket.requester_name.contains(query))
    ).limit(20).all()
    
    # Search knowledge base
    kb_articles = KnowledgeBaseArticle.query.filter(
        (KnowledgeBaseArticle.title.contains(query)) |
        (KnowledgeBaseArticle.content.contains(query))
    ).filter_by(is_published=True).limit(10).all()
    
    # Search assets
    assets = Asset.query.filter(
        (Asset.name.contains(query)) |
        (Asset.serial_number.contains(query)) |
        (Asset.notes.contains(query))
    ).limit(10).all()
    
    return render_template('main/search_results.html',
                           title='Search Results',
                           query=query,
                           tickets=tickets,
                           kb_articles=kb_articles,
                           assets=assets)
